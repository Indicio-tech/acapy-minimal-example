"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
import logging
from os import getenv

from controller import Controller
from controller.logging import logging_to_stdout
from controller.models import (
    ConnRecord,
    ConnectionList,
    InvitationCreateRequest,
    InvitationRecord,
    OobRecord,
)
from controller.protocols import didexchange

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")
LOGGER = logging.getLogger(__name__)


async def reject_after_invite(alice: Controller, bob: Controller):
    """Reject the invitation after receiving it."""
    invite_record = await alice.post(
        "/out-of-band/create-invitation",
        json=InvitationCreateRequest(
            handshake_protocols=["https://didcomm.org/didexchange/1.0"],
            use_public_did=False,
        ),  # pyright: ignore
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
        response=OobRecord,
    )

    bob_conn = await bob.post(
        f"/didexchange/{bob_oob_record.connection_id}/reject",
        response=ConnRecord,
    )
    assert bob_conn.state == "abandoned"


async def reject_after_request(alice: Controller, bob: Controller):
    """Reject after receiving a request."""
    invite_record = await alice.post(
        "/out-of-band/create-invitation",
        json=InvitationCreateRequest(
            handshake_protocols=["https://didcomm.org/didexchange/1.0"],
            use_public_did=False,
        ),  # pyright: ignore
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
        response=OobRecord,
    )

    bob_conn = await bob.post(
        f"/didexchange/{bob_oob_record.connection_id}/accept-invitation",
        response=ConnRecord,
    )
    alice_oob_record = await alice.record_with_values(
        topic="out_of_band",
        record_type=OobRecord,
        connection_id=alice_conn.connection_id,
        state="done",
    )
    alice_conn = await alice.record_with_values(
        topic="connections",
        record_type=ConnRecord,
        rfc23_state="request-received",
        invitation_key=alice_oob_record.our_recipient_key,
    )
    alice_conn = await alice.post(
        f"/didexchange/{alice_conn.connection_id}/reject",
        response=ConnRecord,
    )
    assert alice_conn.state == "abandoned"


async def reject_after_response(alice: Controller, bob: Controller):
    """Reject after receiving a response."""
    invite_record = await alice.post(
        "/out-of-band/create-invitation",
        json=InvitationCreateRequest(
            handshake_protocols=["https://didcomm.org/didexchange/1.0"],
            use_public_did=False,
        ),  # pyright: ignore
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
        response=OobRecord,
    )

    bob_conn = await bob.post(
        f"/didexchange/{bob_oob_record.connection_id}/accept-invitation",
        response=ConnRecord,
    )
    alice_oob_record = await alice.record_with_values(
        topic="out_of_band",
        record_type=OobRecord,
        connection_id=alice_conn.connection_id,
        state="done",
    )
    alice_conn = await alice.record_with_values(
        topic="connections",
        record_type=ConnRecord,
        rfc23_state="request-received",
        invitation_key=alice_oob_record.our_recipient_key,
    )
    alice_conn = await alice.post(
        f"/didexchange/{alice_conn.connection_id}/accept-request",
        response=ConnRecord,
    )
    try:
        alice_conn = await alice.post(
            f"/didexchange/{alice_conn.connection_id}/reject",
            response=ConnRecord,
        )
        exception_raised = False
    except:
        LOGGER.exception("Reject failed")
        exception_raised = True

    assert exception_raised


async def standard(alice: Controller, bob: Controller):
    """Standard DID Exchange."""
    invite_record = await alice.post(
        "/out-of-band/create-invitation",
        json=InvitationCreateRequest(
            handshake_protocols=["https://didcomm.org/didexchange/1.0"],
            use_public_did=False,
        ),  # pyright: ignore
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
        response=OobRecord,
    )

    bob_conn = await bob.post(
        f"/didexchange/{bob_oob_record.connection_id}/accept-invitation",
        response=ConnRecord,
    )
    alice_oob_record = await alice.record_with_values(
        topic="out_of_band",
        record_type=OobRecord,
        connection_id=alice_conn.connection_id,
        state="done",
    )
    # Overwrite multiuse invitation connection with actual connection
    alice_conn = await alice.record_with_values(
        topic="connections",
        record_type=ConnRecord,
        rfc23_state="request-received",
        invitation_key=alice_oob_record.our_recipient_key,
    )
    alice_conn = await alice.post(
        f"/didexchange/{alice_conn.connection_id}/accept-request",
        response=ConnRecord,
    )

    await bob.record_with_values(
        topic="connections",
        connection_id=bob_conn.connection_id,
        rfc23_state="response-received",
    )
    bob_conn = await bob.record_with_values(
        topic="connections",
        connection_id=bob_conn.connection_id,
        rfc23_state="completed",
        record_type=ConnRecord,
    )
    alice_conn = await alice.record_with_values(
        topic="connections",
        connection_id=alice_conn.connection_id,
        rfc23_state="completed",
        record_type=ConnRecord,
    )


async def main():
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        await standard(alice, bob)
        await reject_after_invite(alice, bob)
        await reject_after_request(alice, bob)
        await reject_after_response(alice, bob)


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
