"""Minimal reproducible example script.
This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv
import time
from typing import List

from controller.models import V10PresentationExchangeList

from controller import Controller
from controller.logging import logging_to_stdout
from controller.protocols import (
    connection,
    didexchange,
    indy_anoncred_credential_artifacts,
    indy_anoncred_onboard,
    indy_anoncreds_publish_revocation,
    indy_anoncreds_revoke,
    indy_issue_credential_v1,
    indy_issue_credential_v2,
    indy_present_proof_v1,
    indy_present_proof_v2,
)
import json

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")


def summary(self) -> str:
    return "Summary: " + json.dumps(
        {
            "state": self.state,
            "verified": self.verified,
            "presentation_request": self.presentation_request_dict.dict(by_alias=True),
        },
        indent=2,
        sort_keys=True,
    )


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        # Connecting
        await connection(alice, bob)
        alice_conn, bob_conn = await didexchange(alice, bob)

        # Issuance prep
        await indy_anoncred_onboard(alice)
        schema, cred_def = await indy_anoncred_credential_artifacts(
            alice,
            ["firstname", "lastname"],
            support_revocation=True,
        )

        # Issue the thing
        alice_cred_ex, bob_cred_ex = await indy_issue_credential_v1(
            alice,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            cred_def.credential_definition_id,
            {"firstname": "Bob", "lastname": "Builder"},
        )
        print(alice_cred_ex.json(by_alias=True, indent=2))

        # Issue the thing again in v2
        alice_cred_ex_v2, bob_cred_ex_v2 = await indy_issue_credential_v2(
            alice,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            cred_def.credential_definition_id,
            {"firstname": "Bob", "lastname": "Builder"},
        )
        print(alice_cred_ex.json(by_alias=True, indent=2))
        non_revoked_time = int(time.time())

        # Present the thing
        bob_pres_ex, alice_pres_ex = await indy_present_proof_v1(
            bob,
            alice,
            bob_conn.connection_id,
            alice_conn.connection_id,
            requested_attributes=[{"name": "firstname"}],
        )
        print(alice_pres_ex.json(by_alias=True, indent=2))

        # Present the thing again in v2
        bob_pres_ex_v2, alice_pres_ex_v2 = await indy_present_proof_v2(
            bob,
            alice,
            bob_conn.connection_id,
            alice_conn.connection_id,
            requested_attributes=[{"name": "firstname"}],
        )
        print(alice_pres_ex.json(by_alias=True, indent=2))

        # Revoke credential v1
        await indy_anoncreds_revoke(
            alice,
            cred_ex=alice_cred_ex,
            holder_connection_id=alice_cred_ex.connection_id,
            notify=True,
        )
        await indy_anoncreds_publish_revocation(
            alice, cred_ex=alice_cred_ex
        )
        # TODO: Make this into a helper in protocols.py?
        await bob.record(topic="revocation-notification")

        # Request proof from holder again after revoking
        before_revoking_time = non_revoked_time
        revoked_time = int(time.time())
        (
            bob_pres_ex_v1_entirely_after_int,
            alice_pres_ex_v1_entirely_after_int,
        ) = await indy_present_proof_v1(
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
            non_revoked={"from": revoked_time - 1, "to": revoked_time},
        )

        # Request proof from holder again after revoking,
        # using the interval before cred revoked
        # (non_revoked interval/when cred was valid)
        revoked_time = int(time.time())
        (
            bob_pres_ex_v1_after_revo_using_before_interval,
            alice_pres_ex_v1_after_revo_using_before_interval,
        ) = await indy_present_proof_v1(
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
            non_revoked={"from": before_revoking_time, "to": before_revoking_time},
        )

        # Request proof, no interval
        (
            bob_pres_ex_v1_after_revo_no_interval,
            alice_pres_ex_v1_after_revo_no_interval,
        ) = await indy_present_proof_v1(
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
        (
            bob_pres_ex_v1_after_revo_global_invalid_local_override_w_valid,
            alice_pres_ex_v1_after_revo_global_invalid_local_override_w_valid,
        ) = await indy_present_proof_v1(
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
                        "from": before_revoking_time - 1,
                        "to": before_revoking_time,
                    },
                }
            ],
            non_revoked={"from": revoked_time - 1, "to": revoked_time},
        )

        # Request proof, just local invalid interval
        (
            bob_pres_ex_v1_after_revo_local_invalid,
            alice_pres_ex_v1__local_invalid,
        ) = await indy_present_proof_v1(
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
            "/present-proof/records", response=V10PresentationExchangeList
        )

        # Presentation summary
        for i, pres in enumerate(presentations.results):
            print(summary(pres))
        return presentations



        # Version 2.0
        # Revoke credential v2
        await indy_anoncreds_revoke(
            alice,
            cred_ex=alice_cred_ex_v2,
            holder_connection_id=alice_cred_ex_v2.connection_id,
            notify=True,
            notify_version="v2_0"
        )
        await indy_anoncreds_publish_revocation(
            alice, cred_ex=alice_cred_ex_v2
        )
        # Record again
        await bob.record(topic="revocation-notification")

        # Request proof from holder again after revoking
        before_revoking_time = non_revoked_time
        revoked_time = int(time.time())
        (
            bob_pres_ex_v2_entirely_after_int,
            alice_pres_ex_v2_entirely_after_int,
        ) = await indy_present_proof_v1(
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
            non_revoked={"from": revoked_time - 1, "to": revoked_time},
        )

        # Request proof from holder again after revoking,
        # using the interval before cred revoked
        # (non_revoked interval/when cred was valid)
        revoked_time = int(time.time())
        (
            bob_pres_ex_v2_after_revo_using_before_interval,
            alice_pres_ex_v2_after_revo_using_before_interval,
        ) = await indy_present_proof_v2(
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
            non_revoked={"from": before_revoking_time, "to": before_revoking_time},
        )

        # Request proof, no interval
        (
            bob_pres_ex_v2_after_revo_no_interval,
            alice_pres_ex_v2_after_revo_no_interval,
        ) = await indy_present_proof_v2(
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
        (
            bob_pres_ex_v2_after_revo_global_invalid_local_override_w_valid,
            alice_pres_ex_v2_after_revo_global_invalid_local_override_w_valid,
        ) = await indy_present_proof_v2(
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
                        "from": before_revoking_time - 1,
                        "to": before_revoking_time,
                    },
                }
            ],
            non_revoked={"from": revoked_time - 1, "to": revoked_time},
        )

        # Request proof, just local invalid interval
        (
            bob_pres_ex_v2_after_revo_local_invalid,
            alice_pres_ex_v2_local_invalid,
        ) = await indy_present_proof_v2(
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
        print("###########")
        print("Grabbing presentations now")
        presentations = await alice.get(
            "/present-proof-2.0/records"
        )
        print("here's ur type yo")
        print(type(presentations))
        print(presentations)
        print('un')
        print(presentations[0])
        


        # Presentation summary
        for i, pres in enumerate(presentations.results):
            print(summary(pres))
        return presentations


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
