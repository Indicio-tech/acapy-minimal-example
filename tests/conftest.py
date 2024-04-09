import asyncio
from os import getenv
from typing import Tuple

import pytest
import pytest_asyncio

from acapy_controller.controller import Controller
from acapy_controller.models import (
    ConnRecord,
    CredentialDefinitionSendResult,
    SchemaSendResult,
    V10CredentialExchange,
)
from acapy_controller.protocols import (
    didexchange,
    indy_anoncred_credential_artifacts,
    indy_anoncred_onboard,
    indy_issue_credential_v1,
    indy_issue_credential_v2,
    indy_present_proof_v1,
    indy_present_proof_v2,
)


def getenv_or_raise(var: str) -> str:
    value = getenv(var)
    if value is None:
        raise ValueError(f"Missing environmnet variable: {var}")

    return value


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def alice():
    controller = await Controller(getenv_or_raise("ALICE")).setup()
    yield controller
    await controller.shutdown()


@pytest_asyncio.fixture(scope="session")
async def bob():
    controller = await Controller(getenv_or_raise("BOB")).setup()
    yield controller
    await controller.shutdown()


@pytest_asyncio.fixture(scope="session")
async def did_exchange(alice: Controller, bob: Controller):
    """Testing that dids are exchanged successfully."""
    alice_conn, bob_conn = await didexchange(alice, bob)
    assert alice_conn
    assert bob_conn
    yield alice_conn, bob_conn


@pytest.fixture(scope="session")
def alice_conn(did_exchange: Tuple[ConnRecord, ConnRecord]):
    alice_conn, _ = did_exchange
    yield alice_conn


@pytest.fixture(scope="session")
def bob_conn(did_exchange: Tuple[ConnRecord, ConnRecord]):
    _, bob_conn = did_exchange
    yield bob_conn


@pytest_asyncio.fixture(scope="session")
async def public_did(alice: Controller):
    """Onboard public DID."""
    public_did = await indy_anoncred_onboard(alice)
    assert public_did
    yield public_did


@pytest_asyncio.fixture(scope="session")
async def cred_artifacts(alice: Controller):
    """Testing the preparation of credential artifacts for indy anoncreds."""
    schema, cred_def = await indy_anoncred_credential_artifacts(
        alice,
        ["firstname", "lastname"],
        support_revocation=True,
    )
    assert schema
    assert cred_def
    yield schema, cred_def


@pytest_asyncio.fixture(scope="session")
async def cred_def(
    cred_artifacts: Tuple[SchemaSendResult, CredentialDefinitionSendResult]
):
    _, cred_def = cred_artifacts
    yield cred_def


@pytest_asyncio.fixture(scope="session")
async def alice_cred_ex(
    alice: Controller,
    bob: Controller,
    alice_conn: ConnRecord,
    bob_conn: ConnRecord,
    cred_def: CredentialDefinitionSendResult,
):
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
    yield alice_cred_ex


@pytest_asyncio.fixture(scope="session")
async def alice_cred_ex_v2(
    alice: Controller,
    bob: Controller,
    alice_conn: ConnRecord,
    bob_conn: ConnRecord,
    cred_def: CredentialDefinitionSendResult,
):
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
    yield alice_cred_ex_v2


@pytest_asyncio.fixture(scope="session")
async def alice_pres_ex(
    alice: Controller,
    bob: Controller,
    alice_conn: ConnRecord,
    bob_conn: ConnRecord,
    alice_cred_ex: V10CredentialExchange,
):
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
    yield alice_pres_ex


@pytest_asyncio.fixture(scope="session")
async def alice_pres_ex_v2(
    alice: Controller,
    bob: Controller,
    alice_conn: ConnRecord,
    bob_conn: ConnRecord,
    alice_cred_ex: V10CredentialExchange,
):
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
    yield alice_pres_ex_v2
