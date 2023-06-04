"""Minimal reproducible example script.
This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv
from typing import Mapping, Tuple
from contextlib import AsyncExitStack

from controller import Controller
from controller.logging import logging_to_stdout
from controller.models import (
    ConnRecord,
    CredAttrSpec,
    V20CredExRecord,
    V20CredExRecordDetail,
    V20CredFilter,
    V20CredFilterIndy,
    V20CredOfferRequest,
    V20CredPreview,
)
from controller.protocols import (
    _make_params,
    indy_anoncred_credential_artifacts,
    indy_anoncred_onboard,
)

ALICE = getenv("ALICE", "http://alice:3001")
ALICE0 = getenv("ALICE0", "http://alice0:3001")
ALICE1 = getenv("ALICE1", "http://alice1:3001")
BOB = getenv("BOB", "http://bob:3001")


async def didexchange(
    inviter: Controller,
    invitee: Controller,
    public_did: str,
):
    """Connect two agents using did exchange protocol."""
    invitee_conn = await invitee.post(
        "/didexchange/create-request",
        params=_make_params(
            their_public_did=public_did,
            # use_public_did=True,
        ),
        response=ConnRecord,
    )

    inviter_conn = await inviter.record_with_values(
        topic="connections",
        record_type=ConnRecord,
        rfc23_state="request-received",
    )
    await asyncio.sleep(3)
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

    return inviter_conn, invitee_conn


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
        "/issue-credential-2.0/send",
        json=V20CredOfferRequest(
            auto_issue=True,
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

    # issuer_cred_ex = await issuer.post(
    #     f"/issue-credential-2.0/records/{issuer_cred_ex_id}/issue",
    #     json={},
    #     response=V20CredExRecordDetail,
    # )

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


async def main():
    """Test Controller protocols."""
    async with AsyncExitStack() as stack:
        alice = await stack.enter_async_context(Controller(base_url=ALICE))
        alice0 = await stack.enter_async_context(
            Controller(base_url=ALICE0, event_queue=alice.event_queue)
        )
        alice1 = await stack.enter_async_context(
            Controller(base_url=ALICE1, event_queue=alice.event_queue)
        )
        bob = await stack.enter_async_context(Controller(base_url=BOB))

        # setup public did
        alice_did, bob_did = await asyncio.gather(
            indy_anoncred_onboard(alice),
            indy_anoncred_onboard(bob),
        )

        # Connecting
        bob_conn, alice_conn = await didexchange(bob, alice, bob_did.did)

        schema, cred_def = await indy_anoncred_credential_artifacts(
            alice, ["firstname", "lastname"]
        )
        await indy_issue_credential_v2(
            alice1,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            cred_def.credential_definition_id,
            {"firstname": "bob", "lastname": "builder"},
        )


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
