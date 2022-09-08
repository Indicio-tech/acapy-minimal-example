"""Defintions of protocols flows."""

import logging

from .controller import Controller
from .models import ConnRecord, InvitationResult, PingRequest, ReceiveInvitationRequest


LOGGER = logging.getLogger(__name__)


async def connection(alice: Controller, bob: Controller):
    """Connect two agents."""

    invitation = await alice.post(
        "/connections/create-invitation", json={}, response=InvitationResult
    )
    alice_conn = await alice.get(
        f"/connections/{invitation.connection_id}",
        response=ConnRecord,
    )
    LOGGER.debug("Invitation serialized: %s", invitation.invitation.dict())

    bob_conn = await bob.post(
        "/connections/receive-invitation",
        json=ReceiveInvitationRequest.parse_obj(
            invitation.invitation.dict()
        ),
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
        json=PingRequest(comment="Making connection active")
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
