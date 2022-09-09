"""Defintions of protocols flows."""

from dataclasses import dataclass
import json
import logging
from typing import Any, Mapping, Optional

from .controller import Controller
from .models import (
    ConnRecord,
    ConnectionList,
    InvitationCreateRequest,
    InvitationMessage,
    InvitationRecord,
    InvitationResult,
    PingRequest,
    ReceiveInvitationRequest,
)


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


async def connection(alice: Controller, bob: Controller):
    """Connect two agents."""

    invitation = await alice.post(
        "/connections/create-invitation", json={}, response=InvitationResult
    )
    alice_conn = await alice.get(
        f"/connections/{invitation.connection_id}",
        response=ConnRecord,
    )

    bob_conn = await bob.post(
        "/connections/receive-invitation",
        json=ReceiveInvitationRequest.parse_obj(invitation.invitation.dict()),
        response=ConnRecord,
    )

    await bob.post(
        f"/connections/{bob_conn.connection_id}/accept-invitation",
    )

    await alice.event_queue.get(
        lambda event: event.topic == "connections"
        and event.payload["connection_id"] == alice_conn.connection_id
        and event.payload["rfc23_state"] == "request-received"
    )

    alice_conn = await alice.post(
        f"/connections/{alice_conn.connection_id}/accept-request",
        response=ConnRecord,
    )

    await bob.event_queue.get(
        lambda event: event.topic == "connections"
        and event.payload["connection_id"] == bob_conn.connection_id
        and event.payload["rfc23_state"] == "response-received"
    )
    await bob.post(
        f"/connections/{bob_conn.connection_id}/send-ping",
        json=PingRequest(comment="Making connection active"),
    )

    event = await alice.event_queue.get(
        lambda event: event.topic == "connections"
        and event.payload["connection_id"] == alice_conn.connection_id
        and event.payload["rfc23_state"] == "completed"
    )
    alice_conn = ConnRecord.parse_obj(event.payload)
    event = await bob.event_queue.get(
        lambda event: event.topic == "connections"
        and event.payload["connection_id"] == bob_conn.connection_id
        and event.payload["rfc23_state"] == "completed"
    )
    bob_conn = ConnRecord.parse_obj(event.payload)

    return alice_conn, bob_conn


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
    alice: Controller,
    bob: Controller,
    *,
    invite: Optional[InvitationMessage] = None,
    use_public_did: bool = False,
    auto_accept: Optional[bool] = None,
    multi_use: Optional[bool] = None,
    use_existing_connection: bool = False,
):
    """Connect two agents using did exchange protocol."""
    if not invite:
        invite_record = await alice.post(
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

    alice_conn = (
        await alice.get(
            "/connections",
            params={"invitation_msg_id": invite.id},
            response=ConnectionList,
        )
    ).results[0]

    bob_oob_record = await bob.post(
        "/out-of-band/receive-invitation",
        json=invite,
        params=_make_params(
            use_existing_connection=use_existing_connection,
        ),
        response=OOBRecord,
    )

    if use_existing_connection and bob_oob_record == "reuse-accepted":
        alice_oob_record = OOBRecord(
            **(
                await alice.event_queue.get(
                    lambda event: event.topic == "out_of_band"
                    and event.payload["invi_msg_id"] == invite.id
                )
            ).payload
        )
        alice_conn = await alice.get(
            f"/connections/{alice_oob_record.connection_id}",
            response=ConnRecord,
        )
        bob_conn = await bob.get(
            f"/connections/{bob_oob_record.connection_id}",
            response=ConnRecord,
        )
        return alice_conn, bob_conn

    if not auto_accept:
        bob_conn = await bob.post(
            f"/didexchange/{bob_oob_record.connection_id}/accept-invitation",
            response=ConnRecord,
        )
        alice_oob_record = OOBRecord(**(await alice.event_queue.get(
            lambda event: event.topic == "out_of_band"
            and event.payload["connection_id"] == alice_conn.connection_id
            and event.payload["state"] == "done"
        )).payload)
        alice_conn = await alice.post(
            f"/didexchange/{alice_oob_record.connection_id}/accept-request",
            response=ConnRecord,
        )

        await bob.event_queue.get(
            lambda event: event.topic == "connections"
            and event.payload["connection_id"] == bob_conn.connection_id
            and event.payload["rfc23_state"] == "response-received"
        )
        await bob.event_queue.get(
            lambda event: event.topic == "connections"
            and event.payload["connection_id"] == bob_conn.connection_id
            and event.payload["rfc23_state"] == "completed"
        )
        await alice.event_queue.get(
            lambda event: event.topic == "connections"
            and event.payload["connection_id"] == alice_conn.connection_id
            and event.payload["rfc23_state"] == "completed"
        )
    else:
        bob_conn = await bob.get(
            f"/connections/{bob_oob_record.connection_id}",
            response=ConnRecord,
        )

    return alice_conn, bob_conn
