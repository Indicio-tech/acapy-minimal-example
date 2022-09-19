from secrets import randbelow
from typing import List, NamedTuple, Optional
from uuid import uuid4
import base64
from datetime import datetime
import pytest
import pytest_asyncio
from controller.controller import Controller
from controller.models import (
    ConnRecord,
    CredAttrSpec,
    CredentialDefinitionSendResult,
    IndyCredPrecis,
    IndyProofReqAttrSpec,
    IndyProofRequest,
    SchemaSendResult,
    V20CredExRecord,
    V20CredExRecordDetail,
    V20CredFilter,
    V20CredFilterIndy,
    V20CredOfferRequest,
    V20CredPreview,
    V20PresExRecord,
    V20PresRequestByFormat,
    V20PresSendRequestRequest,
    V20PresSpecByFormatRequest,
)
from controller.protocols import (
    connection,
    indy_anoncred_onboard,
    indy_anoncred_credential_artifacts,
    indy_auto_select_credentials_for_presentation_request,
)


class IssuerHolderInfo(NamedTuple):
    issuer_conn: ConnRecord
    holder_conn: ConnRecord
    schema: SchemaSendResult
    cred_def: CredentialDefinitionSendResult
    issuer_cred_ex: V20CredExRecord


@pytest_asyncio.fixture
async def issue_credential_with_attachment(issuer: Controller, holder: Controller):
    """Test credential issuance with hashlink supplement and attachment."""
    issuer_conn, holder_conn = await connection(issuer, holder)
    await indy_anoncred_onboard(issuer)
    schema, cred_def = await indy_anoncred_credential_artifacts(
        issuer, ["firstname", "lastname", "age", "image"]
    )

    attributes = {
        "firstname": "Bob",
        "lastname": "Builder",
        "age": "42",
        "image": "hl:zQmWvQxTqbG2Z9HPJgG57jjwR154cKhbtJenbyYTWkjgF3e",
    }

    attachment_id = str(uuid4())
    data = b"Hello World!"
    supplement = {
        "type": "hashlink-data",
        "ref": attachment_id,
        "attrs": [{"key": "field", "value": "image"}],
    }
    attachment = {
        "@id": attachment_id,
        "mime-type": "image/jpeg",
        "filename": "face.png",
        "byte_count": len(data),
        "lastmod_time": str(datetime.now()),
        "description": "A picture of a face",
        "data": {"base64": base64.urlsafe_b64encode(data).decode()},
    }
    issuer_cred_ex = await issuer.post(
        "/issue-credential-2.0/send",
        json={
            **V20CredOfferRequest(
                auto_issue=False,
                auto_remove=False,
                comment="Credential from minimal example",
                trace=False,
                connection_id=issuer_conn.connection_id,
                filter=V20CredFilter(  # pyright: ignore
                    indy=V20CredFilterIndy(  # pyright: ignore
                        cred_def_id=cred_def.credential_definition_id,
                    )
                ),
                credential_preview=V20CredPreview(
                    type="issue-credential-2.0/2.0/credential-preview",  # pyright: ignore
                    attributes=[
                        CredAttrSpec(
                            mime_type=None, name=name, value=value  # pyright: ignore
                        )
                        for name, value in attributes.items()
                    ],
                ),
            ).dict(by_alias=True, exclude_none=True, exclude_unset=True),
            "supplements": [supplement],
            "attachments": [attachment],
        },
        response=V20CredExRecord,
    )
    issuer_cred_ex_id = issuer_cred_ex.cred_ex_id

    holder_cred_ex = await holder.record_with_values(
        topic="issue_credential_v2_0",
        record_type=V20CredExRecord,
        connection_id=holder_conn.connection_id,
        state="offer-received",
    )
    holder_cred_ex_id = holder_cred_ex.cred_ex_id

    holder_cred_ex = await holder.post(
        f"/issue-credential-2.0/records/{holder_cred_ex_id}/send-request",
        response=V20CredExRecord,
    )

    await issuer.record_with_values(
        topic="issue_credential_v2_0",
        cred_ex_id=issuer_cred_ex_id,
        state="request-received",
    )

    await holder.record_with_values(
        topic="issue_credential_v2_0",
        cred_ex_id=holder_cred_ex_id,
        state="credential-received",
    )

    holder_cred_ex = await holder.post(
        f"/issue-credential-2.0/records/{holder_cred_ex_id}/store",
        json={},
        response=V20CredExRecordDetail,
    )
    issuer_cred_ex = await issuer.record_with_values(
        topic="issue_credential_v2_0",
        record_type=V20CredExRecord,
        cred_ex_id=issuer_cred_ex_id,
        state="done",
    )

    holder_cred_ex = await holder.record_with_values(
        topic="issue_credential_v2_0",
        record_type=V20CredExRecord,
        cred_ex_id=holder_cred_ex_id,
        state="done",
    )

    yield IssuerHolderInfo(
        issuer_conn,
        holder_conn,
        schema,
        cred_def,
        issuer_cred_ex,
    )


@pytest.mark.asyncio
async def test_issue_credential_with_attachment(issue_credential_with_attachment):
    """Test issuance with attachments."""


class ModifiedV20PresExRecord(V20PresExRecord):
    supplements: Optional[List[dict]] = None
    attachments: Optional[List[dict]] = None


@pytest.mark.asyncio
async def test_presentation_with_attachment(
    issue_credential_with_attachment: IssuerHolderInfo,
    verifier: Controller,
    holder: Controller,
):
    """Test presentation with attachments."""
    requested_attributes = [
        {"name": "firstname"},
        {"name": "image"},
    ]
    verifier_pres_ex = await verifier.post(
        "/present-proof-2.0/send-request",
        json=V20PresSendRequestRequest(
            auto_verify=False,
            comment="Presentation request from minimal",
            connection_id=issue_credential_with_attachment.issuer_conn.connection_id,
            presentation_request=V20PresRequestByFormat(  # pyright: ignore
                indy=IndyProofRequest(
                    name="proof",
                    version="0.1.0",
                    nonce=str(randbelow(10**10)),
                    requested_attributes={
                        str(uuid4()): IndyProofReqAttrSpec.parse_obj(attr)
                        for attr in requested_attributes
                    },
                    requested_predicates={},
                    non_revoked=None,
                ),
            ),
            trace=False,
        ),
        response=ModifiedV20PresExRecord,
    )
    verifier_pres_ex_id = verifier_pres_ex.pres_ex_id

    holder_pres_ex = await holder.record_with_values(
        topic="present_proof_v2_0",
        record_type=ModifiedV20PresExRecord,
        connection_id=issue_credential_with_attachment.holder_conn.connection_id,
        state="request-received",
    )
    assert holder_pres_ex.pres_request
    holder_pres_ex_id = holder_pres_ex.pres_ex_id

    relevant_creds = await holder.get(
        f"/present-proof-2.0/records/{holder_pres_ex_id}/credentials",
        response=List[IndyCredPrecis],
    )
    assert holder_pres_ex.by_format.pres_request
    indy_proof_request = holder_pres_ex.by_format.pres_request["indy"]
    pres_spec = indy_auto_select_credentials_for_presentation_request(
        indy_proof_request, relevant_creds
    )
    holder_pres_ex = await holder.post(
        f"/present-proof-2.0/records/{holder_pres_ex_id}/send-presentation",
        json=V20PresSpecByFormatRequest(  # pyright: ignore
            indy=pres_spec,
            trace=False,
        ),
        response=ModifiedV20PresExRecord,
    )

    await verifier.record_with_values(
        topic="present_proof_v2_0",
        record_type=ModifiedV20PresExRecord,
        pres_ex_id=verifier_pres_ex_id,
        state="presentation-received",
    )
    verifier_pres_ex = await verifier.post(
        f"/present-proof-2.0/records/{verifier_pres_ex_id}/verify-presentation",
        json={},
        response=ModifiedV20PresExRecord,
    )
    verifier_pres_ex = await verifier.record_with_values(
        topic="present_proof_v2_0",
        record_type=ModifiedV20PresExRecord,
        pres_ex_id=verifier_pres_ex_id,
        state="done",
    )

    holder_pres_ex = await holder.record_with_values(
        topic="present_proof_v2_0",
        record_type=ModifiedV20PresExRecord,
        pres_ex_id=holder_pres_ex_id,
        state="done",
    )

    def strip_unique(list_to_strip: List) -> List:
        blocklist = ["lastmod_time", "@id", "id", "ref"]
        new_list = []
        for obj in list_to_strip:
            new_obj = {}
            for key, value in obj.items():
                if key in blocklist:
                    continue
                new_obj[key] = value
            new_list.append(new_obj)
        return new_list

    print(verifier_pres_ex.json(by_alias=True, indent=2))
    print(holder_pres_ex.json(by_alias=True, indent=2))
    assert verifier_pres_ex.verified == "true"
    assert verifier_pres_ex.supplements
    assert verifier_pres_ex.attachments

    issued_creds = issue_credential_with_attachment.issuer_cred_ex
    print(verifier_pres_ex.supplements)
    print(issued_creds.supplements)
    print(verifier_pres_ex.attachments)
    print(issued_creds.attachments)
    assert strip_unique(verifier_pres_ex.supplements) == strip_unique(issued_creds.supplements)
    assert strip_unique(verifier_pres_ex.attachments) == strip_unique(issued_creds.attachments)
