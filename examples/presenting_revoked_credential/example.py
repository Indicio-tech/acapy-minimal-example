"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
import json
from os import getenv
import time

from controller import Controller
from controller.logging import logging_to_stdout
from controller.models import V20PresExRecord, V20PresExRecordList
from controller.protocols import (
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


def summary(presentation: V20PresExRecord) -> str:
    """Summarize a presentation exchange record."""
    request = presentation.pres_request
    return "Summary: " + json.dumps(
        {
            "state": presentation.state,
            "verified": presentation.verified,
            "presentation_request": request.dict(by_alias=True) if request else None,
        },
        indent=2,
        sort_keys=True,
    )


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        # Connecting
        alice_conn, bob_conn = await didexchange(alice, bob)

        # Issuance prep
        await indy_anoncred_onboard(alice)
        schema, cred_def = await indy_anoncred_credential_artifacts(
            alice,
            ["firstname", "lastname"],
            support_revocation=True,
        )

        # Issue a credential
        alice_cred_ex, _ = await indy_issue_credential_v2(
            alice,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            cred_def.credential_definition_id,
            {"firstname": "Bob", "lastname": "Builder"},
        )
        issued_time = int(time.time())

        # Present the the credential's attributes
        await indy_present_proof_v2(
            bob,
            alice,
            bob_conn.connection_id,
            alice_conn.connection_id,
            requested_attributes=[{"name": "firstname"}],
        )

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
        revoked_time = int(time.time())

        # Request proof from holder again after revoking,
        # using the interval before cred revoked
        await indy_present_proof_v2(
            bob,
            alice,
            bob_conn.connection_id,
            alice_conn.connection_id,
            requested_attributes=[
                {
                    "name": "firstname",
                    "restrictions": [
                        {"cred_def_id": cred_def.credential_definition_id}
                    ],
                }
            ],
            non_revoked={"from": issued_time, "to": issued_time},
        )

        # Request proof, no interval
        await indy_present_proof_v2(
            bob,
            alice,
            bob_conn.connection_id,
            alice_conn.connection_id,
            requested_attributes=[
                {
                    "name": "firstname",
                    "restrictions": [
                        {"cred_def_id": cred_def.credential_definition_id}
                    ],
                }
            ],
        )

        # Request proof, using invalid/revoked interval but using
        # local non_revoked override (in requsted attrs)
        # ("LOCAL"-->requested attrs)
        await indy_present_proof_v2(
            bob,
            alice,
            bob_conn.connection_id,
            alice_conn.connection_id,
            requested_attributes=[
                {
                    "name": "firstname",
                    "restrictions": [
                        {"cred_def_id": cred_def.credential_definition_id}
                    ],
                    "non_revoked": {
                        "from": issued_time,
                        "to": issued_time,
                    },
                }
            ],
            non_revoked={"from": revoked_time - 1, "to": revoked_time},
        )

        # Request proof, just local invalid interval
        await indy_present_proof_v2(
            bob,
            alice,
            bob_conn.connection_id,
            alice_conn.connection_id,
            requested_attributes=[
                {
                    "name": "firstname",
                    "restrictions": [
                        {"cred_def_id": cred_def.credential_definition_id}
                    ],
                    "non_revoked": {
                        "from": revoked_time,
                        "to": revoked_time,
                    },
                }
            ],
        )

        # Query presentations
        presentations = await alice.get(
            "/present-proof-2.0/records",
            response=V20PresExRecordList,
        )

        # Presentation summary
        for i, pres in enumerate(presentations.results):
            print(summary(pres))


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
