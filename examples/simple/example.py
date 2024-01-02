"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv
from typing import Optional

from controller import Controller
from controller.logging import logging_to_stdout
from controller.models import (
    ConnRecord,
    ConnectionList,
    InvitationCreateRequest,
    InvitationMessage,
    InvitationRecord,
    OobRecord,
    PingRequest,
)
from controller.protocols import indy_anoncred_onboard, _make_params

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")


async def oob_cv1(
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
            json=InvitationCreateRequest.parse_obj(
                {
                    "handshake_protocols": ["https://didcomm.org/connections/1.0"],
                    "use_public_did": use_public_did,
                }
            ),
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
        response=OobRecord,
    )

    if use_existing_connection and invitee_oob_record.state == "reuse-accepted":
        inviter_oob_record = await inviter.record_with_values(
            topic="out_of_band",
            invi_msg_id=invite.id,
            record_type=OobRecord,
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
            f"/connections/{invitee_oob_record.connection_id}/accept-invitation",
            response=ConnRecord,
        )

        await inviter.record_with_values(
            topic="connections",
            connection_id=inviter_conn.connection_id,
            state="request",
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


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        await indy_anoncred_onboard(alice)
        invite_record = await alice.post(
            "/out-of-band/create-invitation",
            json=InvitationCreateRequest.parse_obj(
                {
                    "handshake_protocols": ["https://didcomm.org/connections/1.0"],
                    "use_public_did": True,
                }
            ),
            params=_make_params(
                auto_accept=True,
                multi_use=True,
            ),
            response=InvitationRecord,
        )
        invite = invite_record.invitation

        await oob_cv1(
            alice,
            bob,
            invite=invite,
            use_public_did=True,
            multi_use=True,
            use_existing_connection=True,
        )
        await oob_cv1(
            alice,
            bob,
            invite=invite,
            use_public_did=True,
            multi_use=True,
            use_existing_connection=True,
        )
        await oob_cv1(
            alice,
            bob,
            invite=invite,
            use_public_did=True,
            multi_use=True,
            use_existing_connection=True,
        )


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
