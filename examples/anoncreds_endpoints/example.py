"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout, section
from acapy_controller.protocols import (
    didexchange,
    indy_anoncred_credential_artifacts,
    indy_anoncred_onboard,
    indy_anoncreds_publish_revocation,
    indy_anoncreds_revoke,
    indy_issue_credential_v2,
    indy_present_proof_v2,
)

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        # Connecting
        with section("Establish connection"):
            alice_conn, bob_conn = await didexchange(alice, bob)

        with section("Create and publish schema and cred def"):
            # Issuance prep
            alice_did = await indy_anoncred_onboard(alice)
            schema, cred_def = await indy_anoncred_credential_artifacts(
                alice,
                ["firstname", "lastname"],
                support_revocation=True,
                issuerID=alice_did.did,
            )

        with section("Issue credential to Bob"):
            # Issue a credential
            alice_cred_ex, _ = await indy_issue_credential_v2(
                alice,
                bob,
                alice_conn.connection_id,
                bob_conn.connection_id,
                cred_def.credential_definition_id,
                {"firstname": "Bob", "lastname": "Builder"},
            )

        with section("Present credential attributes"):
            # Present the the credential's attributes
            await indy_present_proof_v2(
                bob,
                alice,
                bob_conn.connection_id,
                alice_conn.connection_id,
                requested_attributes=[{"name": "firstname"}],
            )

        with section("Revoke credential"):
            # Revoke credential
            await indy_anoncreds_revoke(
                alice,
                cred_ex=alice_cred_ex,
                holder_connection_id=alice_conn.connection_id,
                notify=True,
            )
            await indy_anoncreds_publish_revocation(alice, cred_ex=alice_cred_ex)
            # TODO: Make this into a helper in protocols.py?
            await bob.record(topic="revocation-notification")


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
