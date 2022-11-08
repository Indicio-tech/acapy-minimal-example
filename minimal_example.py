"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from datetime import datetime, timedelta
import json
from os import getenv
from secrets import token_hex
from typing import Optional

from controller import Controller
from controller.logging import logging_to_stdout, section
from controller.models import (
    CredentialDefinitionSendRequest,
    DIDResult,
    SchemaSendRequest,
    TransactionRecord,
    TxnOrCredentialDefinitionSendResult,
    TxnOrSchemaSendResult,
    V10PresentationExchange,
)
from controller.protocols import (
    didexchange,
    indy_anoncred_onboard,
    indy_issue_credential_v1,
    indy_present_proof_v1,
    indy_taa,
)

ENDORSER = getenv("ENDORSER", "http://endorser:3001")
ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://alice:3001")


def presentation_summary(pres_ex: V10PresentationExchange):
    """Print a clean summary of a presentation."""
    return "Summary: " + json.dumps(
        {
            "state": pres_ex.state,
            "verified": pres_ex.verified,
            "presentation_request": (
                pres_ex.presentation_request.dict(by_alias=True)
                if pres_ex.presentation_request
                else None
            ),
            "comment": (
                pres_ex.presentation_request_dict.comment
                if pres_ex.presentation_request_dict
                else None
            ),
        },
        indent=2,
        sort_keys=True,
    )


async def transaction_finished(
    endorser: Controller, author: Controller, transaction_id: Optional[str] = None
):
    """Manually advance transaction endorsement exchange."""

    with section("Advance through transaction endorsement exchange", character="-"):
        if transaction_id:
            created_txn = await author.record_with_values(
                topic="endorse_transaction",
                record_type=TransactionRecord,
                state="transaction_created",
                transaction_id=transaction_id,
            )
        else:
            created_txn = await author.record_with_values(
                topic="endorse_transaction",
                record_type=TransactionRecord,
                state="transaction_created",
            )
            transaction_id = created_txn.transaction_id

        pending_txn = await author.post(
            "/transactions/create-request",
            params={
                "tran_id": created_txn.transaction_id,
                "endorser_write_txn": "false",
            },
            json={"expires_time": str(datetime.now() + timedelta(minutes=1))},
            response=TransactionRecord,
        )

        with section(
            "Endorser receives and accepts transaction", character="_", close="-"
        ):
            endorser_txn_received = await endorser.record_with_values(
                topic="endorse_transaction",
                record_type=TransactionRecord,
                state="request_received",
            )
            endorser_txn_received = await endorser.post(
                f"/transactions/{endorser_txn_received.transaction_id}/endorse",
                response=TransactionRecord,
            )
            endorser_txn_received = await endorser.record_with_values(
                topic="endorse_transaction",
                record_type=TransactionRecord,
                state="transaction_endorsed",
                transaction_id=endorser_txn_received.transaction_id,
            )

        pending_txn = await author.record_with_values(
            topic="endorse_transaction",
            record_type=TransactionRecord,
            state="transaction_endorsed",
            transaction_id=transaction_id,
        )
        txn = await author.post(
            f"/transactions/{pending_txn.transaction_id}/write",
            response=TransactionRecord,
        )
        txn = await author.record_with_values(
            topic="endorse_transaction",
            record_type=TransactionRecord,
            state="transaction_acked",
            transaction_id=transaction_id,
        )
    return txn


async def main():
    """Test Controller protocols."""
    endorser = await Controller(ENDORSER).setup()
    alice = await Controller(ALICE).setup()
    bob = await Controller(BOB).setup()

    with section("Prepare Endorser DID"):
        endorser_did = await indy_anoncred_onboard(endorser)

    with section("Connect Endorser and Alice"):
        endorser_conn, alice_endorser_conn = await didexchange(endorser, alice)

    with section("Establish endorsement roles and info"):
        await alice.post(
            f"/transactions/{alice_endorser_conn.connection_id}/set-endorser-role",
            params={"transaction_my_job": "TRANSACTION_AUTHOR"},
        )
        await endorser.post(
            f"/transactions/{endorser_conn.connection_id}/set-endorser-role",
            params={"transaction_my_job": "TRANSACTION_ENDORSER"},
        )
        await alice.post(
            f"/transactions/{alice_endorser_conn.connection_id}/set-endorser-info",
            params={"endorser_did": endorser_did.did, "endorser_name": "endo"},
        )

    with section("Prepare Alice's DID for issuing"):
        result = await alice.post(
            "/wallet/did/create",
            json={"method": "sov", "options": {"key_type": "ed25519"}},
            response=DIDResult,
        )
        alice_did = result.result
        assert alice_did

    with section("Alice accepts TAA"):
        await indy_taa(alice)

    with section("NYM: Backchannel Alice's DID to the endorser for writing"):
        # WARNING: We're making this request directly to the endorser
        # There are currently issues preventing us from submitting DIDs through an
        # endorser even though recent changes should have implemented this.
        # See: https://github.com/hyperledger/aries-cloudagent-python/issues/2007
        await endorser.post(
            "/ledger/register-nym",
            params={
                "did": alice_did.did,
                "verkey": alice_did.verkey,
            },
        )

    with section("ATTRIB: Set Alice's DID as public"):
        await alice.post(
            "/wallet/did/public",
            params={"did": alice_did.did, "conn_id": alice_endorser_conn.connection_id},
            response=DIDResult,
        )
        await transaction_finished(endorser, alice)

    with section("SCHEMA: Create credential schema"):
        schema_txn = await alice.post(
            "/schemas",
            params={"conn_id": alice_endorser_conn.connection_id},
            json=SchemaSendRequest(
                schema_name="minimal-" + token_hex(8),
                schema_version="1.0",
                attributes=["firstname", "lastname", "age"],
            ),
            response=TxnOrSchemaSendResult,
        )
        assert schema_txn.sent
        assert schema_txn.txn
        await transaction_finished(
            endorser, alice, transaction_id=schema_txn.txn.transaction_id
        )

    with section("CLAIM_DEF: Create credential definition"):
        cred_def_txn = await alice.post(
            "/credential-definitions",
            params={"conn_id": alice_endorser_conn.connection_id},
            json=CredentialDefinitionSendRequest(
                revocation_registry_size=10,
                schema_id=schema_txn.sent.schema_id,
                support_revocation=True,
                tag=token_hex(8),
            ),
            response=TxnOrCredentialDefinitionSendResult,
        )
        await transaction_finished(
            endorser, alice, transaction_id=cred_def_txn.txn.transaction_id
        )

    with section(
        "REVOC_REG_DEF and REVOC_REG_ENTRY: "
        "Complete transaction exchange for automatically created revocation transactions"
    ):
        for _ in range(0, 3):
            await transaction_finished(endorser, alice)

    with section("Connect Alice and Bob"):
        alice_conn, bob_conn = await didexchange(alice, bob)

    with section("Alice issues credential to Bob"):
        alice_cred_ex, bob_cred_ex = await indy_issue_credential_v1(
            alice,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            cred_def_txn.sent.credential_definition_id,
            {"firstname": "Bob", "lastname": "Builder", "age": "42"},
        )

    with section("Alice requests verification from Bob"):
        non_revoked_time = int(datetime.now().timestamp())
        bob_pres_ex, alice_pres_ex = await indy_present_proof_v1(
            bob,
            alice,
            bob_conn.connection_id,
            alice_conn.connection_id,
            requested_attributes=[
                {
                    "name": "firstname",
                    "restrictions": [
                        {"cred_def_id": cred_def_txn.sent.credential_definition_id}
                    ],
                }
            ],
            non_revoked={"from": non_revoked_time, "to": non_revoked_time},
        )

    with section("Final state of presentation exchange (should verify True)"):
        print(presentation_summary(alice_pres_ex))

    with section("REVOC_REG_ENTRY: Alice revokes Bob's credential"):
        await alice.post(
            "/revocation/revoke",
            json={
                "comment": "I'm revoking your credential",
                "cred_rev_id": alice_cred_ex.revocation_id,
                "rev_reg_id": alice_cred_ex.revoc_reg_id,
                "publish": False,
            },
        )
        await alice.post(
            "/revocation/publish-revocations",
        )

    with section("Alice requests verification from Bob after revocation"):
        print("Waiting a few seconds before requesting verification...")
        await asyncio.sleep(10)
        non_revoked_time = int(datetime.now().timestamp())
        bob_pres_ex, alice_pres_ex = await indy_present_proof_v1(
            bob,
            alice,
            bob_conn.connection_id,
            alice_conn.connection_id,
            requested_attributes=[
                {
                    "name": "firstname",
                    "restrictions": [
                        {"cred_def_id": cred_def_txn.sent.credential_definition_id}
                    ],
                }
            ],
            non_revoked={"from": non_revoked_time, "to": non_revoked_time},
        )

    with section("Final state of presentation exchange (should verifiy False)"):
        print(presentation_summary(alice_pres_ex))


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
