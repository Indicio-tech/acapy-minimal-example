import pytest

from controller.controller import Controller
from controller.models import (
    InvitationCreateRequest,
    InvitationRecord,
    PingRequest,
)
from controller.protocols import _make_params, indy_anoncred_onboard, didexchange
from controller.logging import logging_to_stdout


@pytest.mark.asyncio
async def test_multi_use_invite_with_public_did(alice: Controller, faber: Controller):
    """"""

    logging_to_stdout()
    await indy_anoncred_onboard(faber)

    invite_record = await faber.post(
        "/out-of-band/create-invitation",
        json=InvitationCreateRequest(
            handshake_protocols=["https://didcomm.org/didexchange/1.0"],
            use_public_did=True,
        ),
        params=_make_params(
            multi_use=True,
        ),
        response=InvitationRecord,
    )
    invite = invite_record.invitation

    for _ in range(2):
        faber_conn, alice_conn = await didexchange(
            inviter=faber, invitee=alice, invite=invite
        )

        assert faber_conn, alice_conn

        print(faber_conn)
        print(alice_conn)

        faber_conn_id = faber_conn.connection_id
        alice_conn_id = alice_conn.connection_id

        ping = await faber.post(
            f"/connections/{faber_conn_id}/send-ping",
            json=PingRequest(comment="Confirming active connection."),
        )

        assert "thread_id" in ping

        await faber.delete(
            f"/connections/{faber_conn_id}",
        )

        await alice.delete(
            f"/connections/{alice_conn_id}",
        )
