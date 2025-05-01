"""Test protocols."""

from typing import Tuple

import pytest

from acapy_controller import Controller
from acapy_controller.protocols import (
    connection,
    didexchange,
    anoncreds_publish_revocation,
    anoncreds_revoke,
    oob_invitation,
    ConnRecord,
    DIDInfo,
    V10CredentialExchange,
    V10PresentationExchange,
    V20CredExRecordDetail,
    V20PresExRecord,
)


@pytest.mark.asyncio
async def test_connection_established(alice, bob):
    """Testing that connection is established."""
    alice_conn, bob_conn = await connection(alice, bob)
    assert alice_conn.state == "active"
    assert bob_conn.state == "active"


@pytest.mark.asyncio
async def test_did_exchange(did_exchange: Tuple[ConnRecord, ConnRecord]):
    """Testing that dids are exchanged successfully."""
    alice_conn, bob_conn = did_exchange
    assert alice_conn.rfc23_state == "completed"
    assert bob_conn.rfc23_state == "completed"


@pytest.mark.asyncio
async def test_did_exchange_with_multiuse(alice, bob):
    """Testing that dids are exchanged successfully."""
    invite = await oob_invitation(alice, multi_use=True)
    alice_conn, bob_conn = await didexchange(alice, bob, invite=invite)
    assert alice_conn.rfc23_state == "completed"
    assert bob_conn.rfc23_state == "completed"
    alice_conn, bob_conn = await didexchange(alice, bob, invite=invite)
    assert alice_conn.rfc23_state == "completed"
    assert bob_conn.rfc23_state == "completed"


@pytest.mark.asyncio
async def test_indy_anoncred_onboard(public_did: DIDInfo):
    """Testing onboard agent for indy anoncred operations."""


@pytest.mark.asyncio
async def test_indy_issue_credential_v1(alice_cred_ex: V10CredentialExchange):
    """Testing issuing an indy credential using issue-credential/1.0.

    Issuer and holder should already be connected.
    """
    assert alice_cred_ex.state == "credential_acked"


@pytest.mark.asyncio
async def test_indy_issue_credential_v2(alice_cred_ex_v2: V20CredExRecordDetail):
    """Testing issuing an indy credential using issue-credential/2.0.
    Issuer and holder should already be connected.
    """
    assert alice_cred_ex_v2.cred_ex_record.state == "done"


@pytest.mark.asyncio
async def test_indy_indy_present_proof_v1(alice_pres_ex: V10PresentationExchange):
    """Testing presenting an Indy credential using present proof v1."""
    assert alice_pres_ex.state == "verified"


@pytest.mark.asyncio
async def test_indy_present_proof_v2(alice_pres_ex_v2: V20PresExRecord):
    """Testing presenting an Indy credential using present proof v2."""
    assert alice_pres_ex_v2.state == "done"


@pytest.mark.asyncio
async def test_indy_anoncreds_revoke(
    alice: Controller, alice_cred_ex: V10CredentialExchange, alice_conn: ConnRecord
):
    """Testing revoking an Indy credential using revocation revoke."""
    await anoncreds_revoke(
        alice,
        cred_ex=alice_cred_ex,
        holder_connection_id=alice_conn.connection_id,
        notify=True,
    )


@pytest.mark.asyncio
async def test_indy_anoncreds_revoke_v2(
    alice: Controller, alice_cred_ex_v2: V20CredExRecordDetail, alice_conn: ConnRecord
):
    """Testing revoking an Indy credential using revocation revoke."""
    await anoncreds_revoke(
        alice,
        cred_ex=alice_cred_ex_v2,
        holder_connection_id=alice_conn.connection_id,
        notify=True,
    )


@pytest.mark.asyncio
async def test_indy_anoncreds_publish_revocation(
    alice: Controller, alice_cred_ex: V10CredentialExchange
):
    """
    Testing publishing revocation
    """
    await anoncreds_publish_revocation(alice, cred_ex=alice_cred_ex)


@pytest.mark.asyncio
async def test_indy_anoncreds_publish_revocation_v2(
    alice: Controller, alice_cred_ex_v2: V20CredExRecordDetail
):
    """
    Testing publishing revocation
    """
    await anoncreds_publish_revocation(alice, cred_ex=alice_cred_ex_v2)
