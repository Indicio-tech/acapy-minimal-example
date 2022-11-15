import pytest

from controller.controller import Controller
from controller.models import (
    InvitationCreateRequest,
    InvitationRecord,
)
from controller.protocols import _make_params, indy_anoncred_onboard, didexchange


@pytest.mark.asyncio
async def test_multi_use_invite_with_public_did(alice: Controller, faber: Controller):
    """"""
    await indy_anoncred_onboard(faber)

    invite_record = await faber.post(
        "/out-of-band/create-invitation",
        json=InvitationCreateRequest(
            handshake_protocols=["https://didcomm.org/didexchange/1.0"],
            use_public_did=True,
        ),  # pyright: ignore
        params=_make_params(
            # multi_use=True,
        ),
        response=InvitationRecord,
    )
    invite = invite_record.invitation

    faber_conn, alice_conn = await didexchange(
        inviter=faber, invitee=alice  # , invite=invite
    )

    assert faber_conn, alice_conn

    print(faber_conn)
    print(alice_conn)

    ping = await faber.post(
        f"/connections/{faber_conn.connection_id}/send-ping",
    )

    print(ping)
    assert False
