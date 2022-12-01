"""Defintions of protocols flows."""

from dataclasses import dataclass
import json
import logging
from typing import Any, List, Mapping, Optional, Tuple, Union
from uuid import uuid4
from secrets import token_hex, randbelow

from .controller import Controller, ControllerError
from .models import (
    AdminConfig,
    ConnRecord,
    ConnectionList,
    CredAttrSpec,
    CredentialDefinitionSendRequest,
    CredentialDefinitionSendResult,
    CredentialPreview,
    DIDCreate,
    DIDCreateOptions,
    DIDResult,
    IndyCredPrecis,
    IndyPresSpec,
    IndyProofReqAttrSpec,
    IndyProofReqPredSpec,
    IndyProofRequest,
    IndyProofRequestNonRevoked,
    InvitationCreateRequest,
    InvitationMessage,
    InvitationRecord,
    InvitationResult,
    MediationRecord,
    PingRequest,
    ReceiveInvitationRequest,
    SchemaSendRequest,
    SchemaSendResult,
    TAAAccept,
    TAAResult,
    V10CredentialConnFreeOfferRequest,
    V10CredentialExchange,
    V10PresentationExchange,
    V10PresentationSendRequestRequest,
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
from .onboarding import get_onboarder


LOGGER = logging.getLogger(__name__)


def _serialize_param(value: Any):
    return (
        value
        if isinstance(value, (str, int, float)) and not isinstance(value, bool)
        else json.dumps(value)
    )


def _make_params(**kwargs) -> Mapping[str, Any]:
    """Filter out keys with none values from dictionary."""

    return {
        key: _serialize_param(value)
        for key, value in kwargs.items()
        if value is not None
    }


async def connection(inviter: Controller, invitee: Controller):
    """Connect two agents."""

    invitation = await inviter.post(
        "/connections/create-invitation", json={}, response=InvitationResult
    )
    inviter_conn = await inviter.get(
        f"/connections/{invitation.connection_id}",
        response=ConnRecord,
    )

    invitee_conn = await invitee.post(
        "/connections/receive-invitation",
        json=ReceiveInvitationRequest.parse_obj(invitation.invitation.dict()),
        response=ConnRecord,
    )

    await invitee.post(
        f"/connections/{invitee_conn.connection_id}/accept-invitation",
    )

    await inviter.record_with_values(
        topic="connections",
        connection_id=inviter_conn.connection_id,
        rfc23_state="request-received",
    )

    inviter_conn = await inviter.post(
        f"/connections/{inviter_conn.connection_id}/accept-request",
        response=ConnRecord,
    )

    await invitee.record_with_values(
        topic="connections",
        connection_id=invitee_conn.connection_id,
        rfc23_state="response-received",
    )
    await invitee.post(
        f"/connections/{invitee_conn.connection_id}/send-ping",
        json=PingRequest(comment="Making connection active"),
    )

    inviter_conn = await inviter.record_with_values(
        topic="connections",
        record_type=ConnRecord,
        connection_id=inviter_conn.connection_id,
        rfc23_state="completed",
    )
    invitee_conn = await invitee.record_with_values(
        topic="connections",
        record_type=ConnRecord,
        connection_id=invitee_conn.connection_id,
        rfc23_state="completed",
    )

    return inviter_conn, invitee_conn


# TODO No model for OOBRecord in ACA-Py OpenAPI...
@dataclass
class OOBRecord:
    oob_id: str
    state: str
    invi_msg_id: str
    invitation: dict
    connection_id: str
    role: str
    created_at: str
    updated_at: str
    trace: bool
    their_service: Optional[dict] = None
    attach_thread_id: Optional[str] = None
    our_recipient_key: Optional[str] = None


async def didexchange(
    inviter: Controller,
    invitee: Controller,
    *,
    invite: Optional[InvitationMessage] = None,
    use_public_did: bool = False,
    auto_accept: Optional[bool] = None,
    multi_use: Optional[bool] = None,
    use_existing_connection: bool = False,
):
    """Connect two agents using did exchange protocol."""
    if not invite:
        invite_record = await inviter.post(
            "/out-of-band/create-invitation",
            json=InvitationCreateRequest(
                handshake_protocols=["https://didcomm.org/didexchange/1.0"],
                use_public_did=use_public_did,
            ),  # pyright: ignore
            params=_make_params(
                auto_accept=auto_accept,
                multi_use=multi_use,
            ),
            response=InvitationRecord,
        )
        invite = invite_record.invitation

    inviter_conn = (
        await inviter.get(
            "/connections",
            params={"invitation_msg_id": invite.id},
            response=ConnectionList,
        )
    ).results[0]

    invitee_oob_record = await invitee.post(
        "/out-of-band/receive-invitation",
        json=invite,
        params=_make_params(
            use_existing_connection=use_existing_connection,
        ),
        response=OOBRecord,
    )

    if use_existing_connection and invitee_oob_record == "reuse-accepted":
        inviter_oob_record = await inviter.record_with_values(
            topic="out_of_band",
            record_type=OOBRecord,
            invi_msg_id=invite.id,
        )
        inviter_conn = await inviter.get(
            f"/connections/{inviter_oob_record.connection_id}",
            response=ConnRecord,
        )
        invitee_conn = await invitee.get(
            f"/connections/{invitee_oob_record.connection_id}",
            response=ConnRecord,
        )
        return inviter_conn, invitee_conn

    if not auto_accept:
        invitee_conn = await invitee.post(
            f"/didexchange/{invitee_oob_record.connection_id}/accept-invitation",
            response=ConnRecord,
        )
        inviter_oob_record = await inviter.record_with_values(
            topic="out_of_band",
            record_type=OOBRecord,
            connection_id=inviter_conn.connection_id,
            state="done",
        )
        # Overwrite multiuse invitation connection with actual connection
        inviter_conn = await inviter.record_with_values(
            topic="connections",
            record_type=ConnRecord,
            rfc23_state="request-received",
            invitation_key=inviter_oob_record.our_recipient_key,
        )
        inviter_conn = await inviter.post(
            f"/didexchange/{inviter_conn.connection_id}/accept-request",
            response=ConnRecord,
        )

        await invitee.record_with_values(
            topic="connections",
            connection_id=invitee_conn.connection_id,
            rfc23_state="response-received",
        )
        invitee_conn = await invitee.record_with_values(
            topic="connections",
            connection_id=invitee_conn.connection_id,
            rfc23_state="completed",
            record_type=ConnRecord,
        )
        inviter_conn = await inviter.record_with_values(
            topic="connections",
            connection_id=inviter_conn.connection_id,
            rfc23_state="completed",
            record_type=ConnRecord,
        )
    else:
        invitee_conn = await invitee.get(
            f"/connections/{invitee_oob_record.connection_id}",
            response=ConnRecord,
        )

    return inviter_conn, invitee_conn


async def request_mediation_v1(
    mediator: Controller,
    client: Controller,
    mediator_connection_id: str,
    client_connection_id: str,
):
    """Request mediation and await mediation granted."""
    client_record = await client.post(
        f"/mediation/request/{client_connection_id}",
        response=MediationRecord,
    )
    mediator_record = await mediator.record_with_values(
        topic="mediation",
        connection_id=mediator_connection_id,
        record_type=MediationRecord,
    )
    await mediator.post(f"/mediation/requests/{mediator_record.mediation_id}/grant")
    client_record = await client.record_with_values(
        topic="mediation",
        connection_id=client_connection_id,
        mediation_id=client_record.mediation_id,
        state="granted",
        record_type=MediationRecord,
    )
    mediator_record = await mediator.record_with_values(
        topic="mediation",
        connection_id=mediator_connection_id,
        mediation_id=mediator_record.mediation_id,
        state="granted",
        record_type=MediationRecord,
    )
    return mediator_record, client_record


async def indy_anoncred_onboard(agent: Controller):
    """Onboard agent for indy anoncred operations."""

    config = (await agent.get("/status/config", response=AdminConfig)).config
    genesis_url = config.get("ledger.genesis_url")

    if not genesis_url:
        raise ControllerError("No ledger configured on agent")

    taa = (await agent.get("/ledger/taa", response=TAAResult)).result
    if taa.taa_required is True and taa.taa_accepted is None:
        assert taa.taa_record
        await agent.post(
            "/ledger/taa/accept",
            json=TAAAccept(
                mechanism="on_file",
                text=taa.taa_record.text,
                version=taa.taa_record.version,
            ),
        )

    public_did = (await agent.get("/wallet/did/public", response=DIDResult)).result
    if not public_did:
        public_did = (
            await agent.post(
                "/wallet/did/create",
                json=DIDCreate(
                    method="sov", options=DIDCreateOptions(key_type="ed25519")
                ),
                response=DIDResult,
            )
        ).result
        assert public_did

        onboarder = get_onboarder(genesis_url)
        if not onboarder:
            raise ControllerError("Unrecognized ledger, cannot automatically onboard")
        await onboarder.onboard(public_did.did, public_did.verkey)

        await agent.post("/wallet/did/public", params=_make_params(did=public_did.did))

    return public_did


async def indy_anoncred_credential_artifacts(
    agent: Controller,
    attributes: List[str],
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
    cred_def_tag: Optional[str] = None,
    support_revocation: bool = False,
    revocation_registry_size: Optional[int] = None,
):
    """Prepare credential artifacts for indy anoncreds."""
    schema = await agent.post(
        "/schemas",
        json=SchemaSendRequest(
            schema_name=schema_name or "minimal-" + token_hex(8),
            schema_version=schema_version or "1.0",
            attributes=attributes,
        ),
        response=SchemaSendResult,
    )

    cred_def = await agent.post(
        "/credential-definitions",
        json=CredentialDefinitionSendRequest(
            revocation_registry_size=revocation_registry_size,
            schema_id=schema.schema_id,
            support_revocation=support_revocation,
            tag=cred_def_tag or token_hex(8),
        ),
        response=CredentialDefinitionSendResult,
    )

    return schema, cred_def


async def indy_issue_credential_v1(
    issuer: Controller,
    holder: Controller,
    issuer_connection_id: str,
    holder_connection_id: str,
    cred_def_id: str,
    attributes: Mapping[str, str],
) -> Tuple[V10CredentialExchange, V10CredentialExchange]:
    """Issue an indy credential using issue-credential/1.0.
    Issuer and holder should already be connected.
    """
    issuer_cred_ex = await issuer.post(
        "/issue-credential/send-offer",
        json=V10CredentialConnFreeOfferRequest(
            auto_issue=False,
            auto_remove=False,
            comment="Credential from minimal example",
            trace=False,
            connection_id=issuer_connection_id,
            cred_def_id=cred_def_id,
            credential_preview=CredentialPreview(
                type="issue-credential/1.0/credential-preview",  # pyright: ignore
                attributes=[
                    CredAttrSpec(
                        mime_type=None, name=name, value=value  # pyright: ignore
                    )
                    for name, value in attributes.items()
                ],
            ),
        ),
        response=V10CredentialExchange,
    )
    issuer_cred_ex_id = issuer_cred_ex.credential_exchange_id

    holder_cred_ex = await holder.record_with_values(
        topic="issue_credential",
        record_type=V10CredentialExchange,
        connection_id=holder_connection_id,
        state="offer_received",
    )
    holder_cred_ex_id = holder_cred_ex.credential_exchange_id

    holder_cred_ex = await holder.post(
        f"/issue-credential/records/{holder_cred_ex_id}/send-request",
        response=V10CredentialExchange,
    )

    await issuer.record_with_values(
        topic="issue_credential",
        credential_exchange_id=issuer_cred_ex_id,
        state="request_received",
    )

    issuer_cred_ex = await issuer.post(
        f"/issue-credential/records/{issuer_cred_ex_id}/issue",
        json={},
        response=V10CredentialExchange,
    )

    await holder.record_with_values(
        topic="issue_credential",
        credential_exchange_id=holder_cred_ex_id,
        state="credential_received",
    )

    holder_cred_ex = await holder.post(
        f"/issue-credential/records/{holder_cred_ex_id}/store",
        json={},
        response=V10CredentialExchange,
    )
    issuer_cred_ex = await issuer.record_with_values(
        topic="issue_credential",
        record_type=V10CredentialExchange,
        credential_exchange_id=issuer_cred_ex_id,
        state="credential_acked",
    )

    holder_cred_ex = await holder.record_with_values(
        topic="issue_credential",
        record_type=V10CredentialExchange,
        credential_exchange_id=holder_cred_ex_id,
        state="credential_acked",
    )

    return issuer_cred_ex, holder_cred_ex


async def indy_issue_credential_v2(
    issuer: Controller,
    holder: Controller,
    issuer_connection_id: str,
    holder_connection_id: str,
    cred_def_id: str,
    attributes: Mapping[str, str],
) -> Tuple[V20CredExRecord, V20CredExRecord]:
    """Issue an indy credential using issue-credential/2.0.
    Issuer and holder should already be connected.
    """

    issuer_cred_ex = await issuer.post(
        "/issue-credential-2.0/send-offer",
        json=V20CredOfferRequest(
            auto_issue=False,
            auto_remove=False,
            comment="Credential from minimal example",
            trace=False,
            connection_id=issuer_connection_id,
            filter=V20CredFilter(  # pyright: ignore
                indy=V20CredFilterIndy(  # pyright: ignore
                    cred_def_id=cred_def_id,
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
        ),
        response=V20CredExRecord,
    )
    issuer_cred_ex_id = issuer_cred_ex.cred_ex_id

    holder_cred_ex = await holder.record_with_values(
        topic="issue_credential_v2_0",
        record_type=V20CredExRecord,
        connection_id=holder_connection_id,
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

    return issuer_cred_ex, holder_cred_ex


def indy_auto_select_credentials_for_presentation_request(
    presentation_request: Union[IndyProofRequest, dict],
    relevant_creds: List[IndyCredPrecis],
) -> IndyPresSpec:
    """Select credentials to use for presentation automatically."""
    if isinstance(presentation_request, dict):
        presentation_request = IndyProofRequest.parse_obj(presentation_request)

    requested_attributes = {}
    for pres_referrent in presentation_request.requested_attributes.keys():
        for cred_precis in relevant_creds:
            if pres_referrent in cred_precis.presentation_referents:
                requested_attributes[pres_referrent] = {
                    "cred_id": cred_precis.cred_info.referent,
                    "revealed": True,
                }
    requested_predicates = {}
    for pres_referrent in presentation_request.requested_predicates.keys():
        for cred_precis in relevant_creds:
            if pres_referrent in cred_precis.presentation_referents:
                requested_predicates[pres_referrent] = {
                    "cred_id": cred_precis.cred_info.referent,
                }

    return IndyPresSpec.parse_obj(
        {
            "requested_attributes": requested_attributes,
            "requested_predicates": requested_predicates,
            "self_attested_attributes": {},
        }
    )


async def indy_present_proof_v1(
    holder: Controller,
    verifier: Controller,
    holder_connection_id: str,
    verifier_connection_id: str,
    *,
    name: Optional[str] = None,
    version: Optional[str] = None,
    comment: Optional[str] = None,
    requested_attributes: Optional[List[Mapping[str, Any]]] = None,
    requested_predicates: Optional[List[Mapping[str, Any]]] = None,
    non_revoked: Optional[Mapping[str, int]] = None,
):
    """Present an Indy credential using present proof v1."""
    verifier_pres_ex = await verifier.post(
        "/present-proof/send-request",
        json=V10PresentationSendRequestRequest(
            auto_verify=False,
            comment=comment or "Presentation request from minimal",
            connection_id=verifier_connection_id,
            proof_request=IndyProofRequest(
                name=name or "proof",
                version=version or "0.1.0",
                nonce=str(randbelow(10**10)),
                requested_attributes={
                    str(uuid4()): IndyProofReqAttrSpec.parse_obj(attr)
                    for attr in requested_attributes or []
                },
                requested_predicates={
                    str(uuid4()): IndyProofReqPredSpec.parse_obj(pred)
                    for pred in requested_predicates or []
                },
                non_revoked=IndyProofRequestNonRevoked.parse_obj(non_revoked)
                if non_revoked
                else None,
            ),
            trace=False,
        ),
        response=V10PresentationExchange,
    )
    verifier_pres_ex_id = verifier_pres_ex.presentation_exchange_id

    holder_pres_ex = await holder.record_with_values(
        topic="present_proof",
        record_type=V10PresentationExchange,
        connection_id=holder_connection_id,
        state="request_received",
    )
    assert holder_pres_ex.presentation_request
    holder_pres_ex_id = holder_pres_ex.presentation_exchange_id

    relevant_creds = await holder.get(
        f"/present-proof/records/{holder_pres_ex_id}/credentials",
        response=List[IndyCredPrecis],
    )
    pres_spec = indy_auto_select_credentials_for_presentation_request(
        holder_pres_ex.presentation_request, relevant_creds
    )
    holder_pres_ex = await holder.post(
        f"/present-proof/records/{holder_pres_ex_id}/send-presentation",
        json=pres_spec,
        response=V10PresentationExchange,
    )

    await verifier.record_with_values(
        topic="present_proof",
        record_type=V10PresentationExchange,
        presentation_exchange_id=verifier_pres_ex_id,
        state="presentation_received",
    )
    verifier_pres_ex = await verifier.post(
        f"/present-proof/records/{verifier_pres_ex_id}/verify-presentation",
        json={},
        response=V10PresentationExchange,
    )
    verifier_pres_ex = await verifier.record_with_values(
        topic="present_proof",
        record_type=V10PresentationExchange,
        presentation_exchange_id=verifier_pres_ex_id,
        state="verified",
    )

    holder_pres_ex = await holder.record_with_values(
        topic="present_proof",
        record_type=V10PresentationExchange,
        presentation_exchange_id=holder_pres_ex_id,
        state="presentation_acked",
    )

    return holder_pres_ex, verifier_pres_ex


async def indy_present_proof_v2(
    holder: Controller,
    verifier: Controller,
    holder_connection_id: str,
    verifier_connection_id: str,
    *,
    name: Optional[str] = None,
    version: Optional[str] = None,
    comment: Optional[str] = None,
    requested_attributes: Optional[List[Mapping[str, Any]]] = None,
    requested_predicates: Optional[List[Mapping[str, Any]]] = None,
    non_revoked: Optional[Mapping[str, int]] = None,
):
    """Present an Indy credential using present proof v2."""
    verifier_pres_ex = await verifier.post(
        "/present-proof-2.0/send-request",
        json=V20PresSendRequestRequest(
            auto_verify=False,
            comment=comment or "Presentation request from minimal",
            connection_id=verifier_connection_id,
            presentation_request=V20PresRequestByFormat(  # pyright: ignore
                indy=IndyProofRequest(
                    name=name or "proof",
                    version=version or "0.1.0",
                    nonce=str(randbelow(10**10)),
                    requested_attributes={
                        str(uuid4()): IndyProofReqAttrSpec.parse_obj(attr)
                        for attr in requested_attributes or []
                    },
                    requested_predicates={
                        str(uuid4()): IndyProofReqPredSpec.parse_obj(pred)
                        for pred in requested_predicates or []
                    },
                    non_revoked=IndyProofRequestNonRevoked.parse_obj(non_revoked)
                    if non_revoked
                    else None,
                ),
            ),
            trace=False,
        ),
        response=V20PresExRecord,
    )
    verifier_pres_ex_id = verifier_pres_ex.pres_ex_id

    holder_pres_ex = await holder.record_with_values(
        topic="present_proof_v2_0",
        record_type=V20PresExRecord,
        connection_id=holder_connection_id,
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
        response=V20PresExRecord,
    )

    await verifier.record_with_values(
        topic="present_proof_v2_0",
        record_type=V20PresExRecord,
        pres_ex_id=verifier_pres_ex_id,
        state="presentation-received",
    )
    verifier_pres_ex = await verifier.post(
        f"/present-proof-2.0/records/{verifier_pres_ex_id}/verify-presentation",
        json={},
        response=V20PresExRecord,
    )
    verifier_pres_ex = await verifier.record_with_values(
        topic="present_proof_v2_0",
        record_type=V20PresExRecord,
        pres_ex_id=verifier_pres_ex_id,
        state="done",
    )

    holder_pres_ex = await holder.record_with_values(
        topic="present_proof_v2_0",
        record_type=V20PresExRecord,
        pres_ex_id=holder_pres_ex_id,
        state="done",
    )

    return holder_pres_ex, verifier_pres_ex

async def indy_anoncreds_revoke(
    issuer: Controller,
    cred_ex: Union[V10CredentialExchange, V20CredExRecordDetail],
    holder_connection_id: Optional[str] = None,
    publish: bool = False,
    notify: bool = True,
    notify_version: str = "v1_0"
):
    """Revoking an Indy credential using revocation revoke.
    V1.0: V10CredentialExchange
    V2.0: V20CredExRecordDetail
    """
    if notify==True and holder_connection_id is None:
        return(
            "If you are going to set notify to True,"
            "then holder_connection_id cannot be empty."
            )

    # Passes in V10CredentialExchange
    if isinstance(cred_ex, V10CredentialExchange):
        await issuer.post(
            url="/revocation/revoke",
            json={
                "connection_id":holder_connection_id,
                "rev_reg_id":cred_ex.revoc_reg_id,
                "cred_rev_id":cred_ex.revocation_id,
                "publish":publish,
                "notify":notify,
                "notify_version":notify_version
            }
        )

    # Passes in V20CredExRecordDetail
    elif isinstance(cred_ex, V20CredExRecordDetail) and cred_ex.indy:
        await issuer.post(
            url="/revocation/revoke",
            json={
                "connection_id":holder_connection_id,
                "rev_reg_id":cred_ex.indy.rev_reg_id,
                "cred_rev_id":cred_ex.indy.cred_rev_id,
                "publish":publish,
                "notify":notify,
                "notify_version":notify_version
            }
        )
        
    else:
        raise ValueError(
            "If using V1.0, try passing in a V10CredentialExchange object. If using V2.0, try passing in a V20CredExRecordDetail object."
        )


async def indy_anoncreds_publish_revocation(
    issuer: Controller,
    cred_ex: Union[V10CredentialExchange, V20CredExRecordDetail],
    publish: bool = False,
    notify: bool = True,
):
    """Publishing revocation of indy credential
    V1.0: V10CredentialExchange
    V2.0: V20CredExRecordDetail
    """
    if isinstance(cred_ex, V10CredentialExchange):
        await issuer.post(
            url="/revocation/publish-revocations",
            json={
                "rev_reg_id":cred_ex.revoc_reg_id,
                "cred_rev_id":cred_ex.revocation_id,
                "publish":publish,
                "notify":notify
            }
        )

    elif isinstance(cred_ex, V20CredExRecordDetail) and cred_ex.indy:
        await issuer.post(
            url="/revocation/publish-revocations",
            json={
                "rev_reg_id":cred_ex.indy.rev_reg_id,
                "cred_rev_id":cred_ex.indy.cred_rev_id,
                "publish":publish,
                "notify":notify
            }
        )
        
    else:
        raise ValueError(
            "If using V1.0, try passing in a V10CredentialExchange object. If using V2.0, try passing in a V20CredExRecordDetail object."
        )
