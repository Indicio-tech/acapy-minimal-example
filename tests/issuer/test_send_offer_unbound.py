import pytest
from controller.controller import Controller
from uuid import uuid4
import base64
from datetime import datetime
from controller.protocols import (
    connection,
    indy_anoncred_onboard,
    indy_anoncred_credential_artifacts,
)
from controller.models import (
    CredAttrSpec,
    V20CredExRecord,
    V20CredExRecordDetail,
    V20CredFilter,
    V20CredFilterIndy,
    V20CredOfferRequest,
    V20CredPreview,
)


@pytest.mark.asyncio
async def test_send_offer_unbound_with_attachment(
    issuer: Controller, holder: Controller
):
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
    supplement_id = str(uuid4())
    data = b"Hello World!"
    supplement = {
        "type": "hashlink-data",
        "ref": attachment_id,
        "attrs": [{"key": "field", "value": "image"}],
        "@id": supplement_id,
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
        "/issue-credential-2.0/send-offer",
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

    issuer_cred_ex = await issuer.post(
        f"/issue-credential-2.0/records/{issuer_cred_ex_id}/issue",
        json={},
        response=V20CredExRecordDetail,
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

    assert holder_cred_ex.attachments
    assert issuer_cred_ex.attachments

    assert holder_cred_ex.supplements
    assert issuer_cred_ex.supplements

    assert holder_cred_ex.attachments == [attachment]
    assert issuer_cred_ex.attachments == [attachment]

    assert holder_cred_ex.supplements == [supplement]
    assert issuer_cred_ex.supplements == [supplement]
