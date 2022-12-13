#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 21 12:16:49 2022
@author: Alexandra N. Walker
Testing methods from protocols.py
"""
from controller.protocols import (
    connection,
    didexchange,
    indy_anoncred_onboard,
    indy_anoncred_credential_artifacts,
    indy_issue_credential_v1,
    indy_issue_credential_v2,
    indy_present_proof_v1,
    indy_present_proof_v2,
    indy_anoncreds_revoke,
    indy_anoncreds_publish_revocation
    )
from tests.conftest import (
    getenv_or_raise,
    alice,
    bob
)
from controller.controller import Controller
import pytest
import pytest_asyncio
from os import getenv

@pytest.mark.asyncio
async def test_connection_established(alice,bob):
    """Testing that connection is established."""
    alice_conn, bob_conn = await connection(alice, bob)
    assert alice_conn
    assert bob_conn
    yield alice_conn, bob_conn
    
@pytest.mark.asyncio
async def test_did_exchange(alice,bob):
    """Testing that dids are exchanged successfully."""
    alice_conn, bob_conn = await didexchange(alice, bob)
    assert alice_conn
    assert bob_conn
    yield alice_conn, bob_conn

@pytest.mark.asyncio
async def test_did_exchange_with_multiuse(alice,bob):
    """Testing that dids are exchanged successfully."""
    alice_conn, bob_conn = await didexchange(alice, bob, multi_use=True)
    assert alice_conn
    assert bob_conn
    yield alice_conn, bob_conn
    
@pytest_asyncio.fixture
async def did_exchange(alice,bob):
    """Testing that dids are exchanged successfully."""
    alice_conn, bob_conn = await didexchange(alice, bob)
    assert alice_conn
    assert bob_conn
    yield alice_conn, bob_conn
    
@pytest_asyncio.fixture
async def alice_conn(alice,bob,did_exchange):
    alice_conn, bob_conn = did_exchange
    yield alice_conn
    
@pytest_asyncio.fixture
async def bob_conn(alice,bob,did_exchange):
    alice_conn, bob_conn = did_exchange
    yield bob_conn

@pytest.mark.asyncio
async def test_indy_anoncred_onboard(alice,bob):
    """"Testing onboard agent for indy anoncred operations."""
    public_did = await indy_anoncred_onboard(agent=alice)
    assert public_did
    return public_did

@pytest.mark.asyncio
async def test_indy_anoncred_credential_artifacts(alice,bob):
    """Testing the preparation of credential artifacts for indy anoncreds."""
    schema, cred_def = await indy_anoncred_credential_artifacts(
           alice,
           ["firstname", "lastname"],
           support_revocation=True,
       )
    assert schema
    assert cred_def
    yield schema, cred_def
    
@pytest_asyncio.fixture
async def fixture_indy_anoncred_credential_artifacts(alice,bob):
    """Testing the preparation of credential artifacts for indy anoncreds."""
    schema, cred_def = await indy_anoncred_credential_artifacts(
           alice,
           ["firstname", "lastname"],
           support_revocation=True,
       )
    assert schema
    assert cred_def
    yield schema, cred_def

@pytest_asyncio.fixture
async def cred_def(alice,bob,fixture_indy_anoncred_credential_artifacts):
    schema, cred_def = fixture_indy_anoncred_credential_artifacts
    yield cred_def

@pytest.mark.asyncio
async def test_indy_issue_credential_v1(alice,bob,alice_conn,bob_conn,cred_def):
    """Testing issuing an indy credential using issue-credential/1.0.
    Issuer and holder should already be connected.
    """
    alice_cred_ex, bob_cred_ex = await indy_issue_credential_v1(
            alice,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            cred_def.credential_definition_id,
            {"firstname": "Bob", "lastname": "Builder"},
        )
    
    assert alice_cred_ex
    assert bob_cred_ex
    return alice_cred_ex, bob_cred_ex

@pytest.mark.asyncio
async def test_indy_issue_credential_v2(alice,bob,alice_conn,bob_conn,cred_def):
    """Testing issuing an indy credential using issue-credential/2.0.
    Issuer and holder should already be connected.
    """
    alice_cred_ex_v2, bob_cred_ex_v2 = await indy_issue_credential_v2(
            alice,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            cred_def.credential_definition_id,
            {"firstname": "Bob", "lastname": "Builder"},
        )

    assert alice_cred_ex_v2
    assert bob_cred_ex_v2
    return alice_cred_ex_v2, bob_cred_ex_v2


@pytest.mark.asyncio
async def test_indy_indy_present_proof_v1(alice,bob,alice_conn,bob_conn):
    """Testing presenting an Indy credential using present proof v1."""
    bob_pres_ex, alice_pres_ex = await indy_present_proof_v1(
        bob,
        alice,
        bob_conn.connection_id,
        alice_conn.connection_id,
        requested_attributes=[{"name": "firstname"}],
    )
    assert bob_pres_ex
    assert alice_pres_ex
    return bob_pres_ex, alice_pres_ex

@pytest_asyncio.fixture
async def fixture_indy_present_proof_v1(alice,bob,alice_conn,bob_conn):
    """Testing presenting an Indy credential using present proof v1."""
    bob_pres_ex, alice_pres_ex = await indy_present_proof_v1(
        bob,
        alice,
        bob_conn.connection_id,
        alice_conn.connection_id,
        requested_attributes=[{"name": "firstname"}],
    )
    assert bob_pres_ex
    assert alice_pres_ex
    return bob_pres_ex, alice_pres_ex

@pytest.mark.asyncio
async def test_indy_present_proof_v2(alice,bob,alice_conn,bob_conn):
    """Testing presenting an Indy credential using present proof v2."""
    bob_pres_ex_v2, alice_pres_ex_v2 = await indy_present_proof_v2(
        bob,
        alice,
        bob_conn.connection_id,
        alice_conn.connection_id,
        requested_attributes=[{"name": "firstname"}],
    )
    assert bob_pres_ex_v2
    assert alice_pres_ex_v2
    return bob_pres_ex_v2, alice_pres_ex_v2

@pytest_asyncio.fixture
async def fixture_indy_present_proof_v2(alice,bob,alice_conn,bob_conn):
    """Testing presenting an Indy credential using present proof v2."""
    bob_pres_ex_v2, alice_pres_ex_v2 = await indy_present_proof_v2(
        bob,
        alice,
        bob_conn.connection_id,
        alice_conn.connection_id,
        requested_attributes=[{"name": "firstname"}],
    )
    assert bob_pres_ex_v2
    assert alice_pres_ex_v2
    return bob_pres_ex_v2, alice_pres_ex_v2

@pytest.fixture
async def alice_cred_ex(alice,bob,fixture_indy_present_proof_v1):
    bob_pres_ex, alice_pres_ex = fixture_indy_present_proof_v1
    yield alice_pres_ex
    
@pytest.fixture
async def alice_cred_ex_v2(alice,bob,fixture_indy_present_proof_v2):
    bob_pres_ex_v2, alice_pres_ex_v2 = fixture_indy_present_proof_v2
    yield alice_pres_ex_v2
    
@pytest.fixture
async def bob_cred_ex(alice,bob,fixture_indy_present_proof_v1):
    bob_pres_ex, alice_pres_ex = fixture_indy_present_proof_v1
    yield bob_pres_ex
    
@pytest.fixture
async def bob_cred_ex_v2(alice,bob,fixture_indy_present_proof_v1):
    bob_pres_ex_v2, alice_pres_ex_v2 = fixture_indy_present_proof_v2
    yield bob_pres_ex_v2
    
@pytest.mark.asyncio
async def test_indy_anoncreds_revoke(alice,alice_cred_ex,bob_cred_ex):
    """Testing revoking an Indy credential using revocation revoke.
    """
    test_revoke_cred_either_version = await indy_anoncreds_revoke(
            alice,
            cred_ex=alice_cred_ex,
            holder_connection_id=bob_cred_ex.connection_id,
            notify=True,
        )
    assert test_revoke_cred_either_version
    yield test_revoke_cred_either_version
    
@pytest.mark.asyncio
async def test_indy_anoncreds_revoke_v2(alice,alice_cred_ex_v2,bob_cred_ex_v2):
    """Testing revoking an Indy credential using revocation revoke.
    """
    test_revoke_cred_either_version = await indy_anoncreds_revoke(
            alice,
            cred_ex=alice_cred_ex_v2,
            holder_connection_id=bob_cred_ex_v2.connection_id,
            notify=True,
        )
    assert test_revoke_cred_either_version
    yield test_revoke_cred_either_version

@pytest.mark.asyncio
async def test_indy_anoncreds_publish_revocation(alice,alice_cred_ex):
    """
    Testing publishing revocation
    """
    test_publish_revocation_either_version = await indy_anoncreds_publish_revocation(
            alice, cred_ex=alice_cred_ex
        )
    assert test_publish_revocation_either_version
    yield test_publish_revocation_either_version
    
@pytest.mark.asyncio
async def test_indy_anoncreds_publish_revocation_v2(alice,alice_cred_ex_v2):
    """
    Testing publishing revocation
    """
    test_publish_revocation_either_version = await indy_anoncreds_publish_revocation(
            alice, cred_ex=alice_cred_ex_v2
        )
    assert test_publish_revocation_either_version
    yield test_publish_revocation_either_version
