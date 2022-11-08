from secrets import token_hex
from typing import List, Optional, Tuple
import pytest
import pytest_asyncio
from datetime import datetime, timedelta

from controller import Controller
from controller.models import (
    DID,
    ConnRecord,
    CredentialDefinitionSendRequest,
    DIDResult,
    RevRegResult,
    SchemaSendRequest,
    TransactionRecord,
    TxnOrCredentialDefinitionSendResult,
    TxnOrRevRegResult,
    TxnOrSchemaSendResult,
)
from controller.protocols import (
    indy_anoncred_onboard,
    didexchange,
    indy_taa,
    indy_issue_credential_v1,
)
from controller.logging import logging_to_stdout


@pytest_asyncio.fixture(scope="session")
async def endorser_did(endorser: Controller):
    public_did = await indy_anoncred_onboard(endorser)
    yield public_did


@pytest_asyncio.fixture(scope="session")
async def endorser_alice_connection(endorser: Controller, alice: Controller):
    yield await didexchange(endorser, alice)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def endorsed_did(
    endorser: Controller,
    alice: Controller,
    endorser_alice_connection: Tuple[ConnRecord, ConnRecord],
    endorser_did: DID,
):
    endorser_conn, alice_conn = endorser_alice_connection

    # Establish roles
    await alice.post(
        f"/transactions/{alice_conn.connection_id}/set-endorser-role",
        params={"transaction_my_job": "TRANSACTION_AUTHOR"},
    )
    await endorser.post(
        f"/transactions/{endorser_conn.connection_id}/set-endorser-role",
        params={"transaction_my_job": "TRANSACTION_ENDORSER"},
    )

    # Establish endorser DID to include in transactions to later be signed with
    await alice.post(
        f"/transactions/{alice_conn.connection_id}/set-endorser-info",
        params={"endorser_did": endorser_did.did, "endorser_name": "endo"},
    )
    result = await alice.post(
        "/wallet/did/create",
        json={"method": "sov", "options": {"key_type": "ed25519"}},
        response=DIDResult,
    )
    alice_did = result.result
    assert alice_did

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
    await indy_taa(alice)

    await alice.post(
        "/wallet/did/public",
        params={"did": alice_did.did, "conn_id": alice_conn.connection_id},
        response=DIDResult,
    )
    await process_pending_txn(endorser, alice)
    yield alice_did


async def process_pending_txn(endorser: Controller, author: Controller):
    """Process a pending transaction."""
    pending_txn = await author.record_with_values(
        topic="endorse_transaction",
        record_type=TransactionRecord,
        state="transaction_created",
    )
    pending_txn = await author.post(
        "/transactions/create-request",
        params={"tran_id": pending_txn.transaction_id, "endorser_write_txn": "false"},
        json={"expires_time": str(datetime.now() + timedelta(minutes=1))},
        response=TransactionRecord,
    )
    endorser_txn_received = await endorser.record_with_values(
        topic="endorse_transaction",
        record_type=TransactionRecord,
        state="request_received",
    )
    endorser_txn_received = await endorser.post(
        f"/transactions/{endorser_txn_received.transaction_id}/endorse",
        response=TransactionRecord,
    )
    pending_txn = await author.record_with_values(
        topic="endorse_transaction",
        record_type=TransactionRecord,
        state="transaction_endorsed",
    )
    txn = await author.post(
        f"/transactions/{pending_txn.transaction_id}/write",
        response=TransactionRecord,
    )
    return txn


async def indy_anoncred_credential_artifacts_through_endorser(
    agent: Controller,
    endorser: Controller,
    endorser_connection_id: str,
    attributes: List[str],
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
    cred_def_tag: Optional[str] = None,
    support_revocation: bool = False,
    revocation_registry_size: Optional[int] = None,
):
    """Prepare credential artifacts for indy anoncreds."""
    schema_txn = await agent.post(
        "/schemas",
        params={"conn_id": endorser_connection_id},
        json=SchemaSendRequest(
            schema_name=schema_name or "minimal-" + token_hex(8),
            schema_version=schema_version or "1.0",
            attributes=attributes,
        ),
        response=TxnOrSchemaSendResult,
    )
    assert schema_txn.sent
    await process_pending_txn(endorser, agent)

    cred_def_txn = await agent.post(
        "/credential-definitions",
        params={"conn_id": endorser_connection_id},
        json=CredentialDefinitionSendRequest(
            revocation_registry_size=revocation_registry_size,
            schema_id=schema_txn.sent.schema_id,
            support_revocation=support_revocation,
            tag=cred_def_tag or token_hex(8),
        ),
        response=TxnOrCredentialDefinitionSendResult,
    )
    assert cred_def_txn.sent
    await process_pending_txn(endorser, agent)
    # When automatically sending revocation txns, we need to process them here
    if support_revocation:
        for _ in range(0, 3):
            await process_pending_txn(endorser, agent)

    return schema_txn.sent, cred_def_txn.sent


async def indy_anoncred_prepare_revoc_registry(
    agent: Controller,
    endorser: Controller,
    endorser_connection_id: str,
    cred_def_id: str,
    revoc_reg_size: int = 1000,
):
    rev_reg_result = await agent.post(
        "/revocation/create-registry",
        json={
            "credential_definition_id": cred_def_id,
            "max_cred_num": revoc_reg_size,
        },
        response=RevRegResult,
    )
    rev_reg = rev_reg_result.result
    await agent.post(
        f"/revocation/registry/{rev_reg.revoc_reg_id}/definition",
        params={"conn_id": endorser_connection_id},
        response=TxnOrRevRegResult,
    )
    await process_pending_txn(endorser, agent)
    return rev_reg


@pytest.mark.asyncio
async def test_endorsed_did(endorsed_did: DID):
    assert endorsed_did


@pytest.mark.asyncio
async def test_issue_credential(
    endorser: Controller,
    alice: Controller,
    bob: Controller,
    endorser_alice_connection: Tuple[ConnRecord, ConnRecord],
):
    _, alice_conn = endorser_alice_connection
    schema, cred_def = await indy_anoncred_credential_artifacts_through_endorser(
        alice,
        endorser,
        alice_conn.connection_id,
        attributes=[
            "firstname",
            "lastname",
            "age",
        ],
    )
    alice_bob_conn, bob_conn = await didexchange(alice, bob)
    alice_cred_ex, bob_cred_ex = await indy_issue_credential_v1(
        issuer=alice,
        holder=bob,
        issuer_connection_id=alice_bob_conn.connection_id,
        holder_connection_id=bob_conn.connection_id,
        cred_def_id=cred_def.credential_definition_id,
        attributes={"firstname": "Bob", "lastname": "Builder", "age": "42"},
    )
    assert bob_cred_ex.state == "credential_acked"


@pytest.mark.asyncio
async def test_issue_revocable_credential(
    endorser: Controller,
    alice: Controller,
    bob: Controller,
    endorser_alice_connection: Tuple[ConnRecord, ConnRecord],
):
    logging_to_stdout()
    _, alice_conn = endorser_alice_connection
    schema, cred_def = await indy_anoncred_credential_artifacts_through_endorser(
        alice,
        endorser,
        alice_conn.connection_id,
        attributes=[
            "firstname",
            "lastname",
            "age",
        ],
        support_revocation=True,
    )
    # rev_reg = await indy_anoncred_prepare_revoc_registry(
    #     alice,
    #     endorser,
    #     alice_conn.connection_id,
    #     cred_def.credential_definition_id,
    #     revoc_reg_size=5,
    # )
    alice_bob_conn, bob_conn = await didexchange(alice, bob)
    alice_cred_ex, bob_cred_ex = await indy_issue_credential_v1(
        issuer=alice,
        holder=bob,
        issuer_connection_id=alice_bob_conn.connection_id,
        holder_connection_id=bob_conn.connection_id,
        cred_def_id=cred_def.credential_definition_id,
        attributes={"firstname": "Bob", "lastname": "Builder", "age": "42"},
    )
    assert bob_cred_ex.state == "credential_acked"
    assert False
