"""Test Public DID Mediator info."""

from typing import Tuple
import pytest
import pytest_asyncio
from controller.controller import Controller
from controller.models import (
    DID,
    AdminConfig,
    DIDCreate,
    DIDCreateOptions,
    DIDResult,
    MediationRecord,
    ResolutionResult,
    TAAAccept,
    TAAResult,
)
from controller.onboarding import get_onboarder
from controller.protocols import request_mediation_v1, connection


@pytest_asyncio.fixture
async def mediation_established(alice: Controller, mediator: Controller):
    """Establish mediation."""
    alice_conn, mediator_conn = await connection(alice, mediator)

    mediator_record, client_record = await request_mediation_v1(
        mediator, alice, mediator_conn.connection_id, alice_conn.connection_id
    )
    yield mediator_record, client_record


@pytest_asyncio.fixture
async def genesis_url(alice: Controller):
    """Retrieve genesis url."""
    config = (await alice.get("/status/config", response=AdminConfig)).config
    genesis_url = config.get("ledger.genesis_url")

    assert genesis_url
    yield genesis_url


@pytest_asyncio.fixture
async def signed_taa(alice: Controller):
    """Establish mediation."""
    taa = (await alice.get("/ledger/taa", response=TAAResult)).result
    if taa.taa_required is True and taa.taa_accepted is None:
        assert taa.taa_record
        await alice.post(
            "/ledger/taa/accept",
            json=TAAAccept(
                mechanism="on_file",
                text=taa.taa_record.text,
                version=taa.taa_record.version,
            ),
        )


@pytest.mark.asyncio
async def test_mediation_established(mediation_established):
    """Test that mediation can be established."""
    assert mediation_established


@pytest_asyncio.fixture
async def public_did_with_mediator(
    alice: Controller,
    mediator: Controller,
    mediation_established: Tuple[MediationRecord, MediationRecord],
    genesis_url: str,
    signed_taa: None,
):
    """Get a public DID with mediation."""
    _, alice_mediation_record = mediation_established
    did = (
        await alice.post(
            "/wallet/did/create",
            json=DIDCreate(method="sov", options=DIDCreateOptions(key_type="ed25519")),
            response=DIDResult,
        )
    ).result
    assert did

    onboarder = get_onboarder(genesis_url)
    assert onboarder
    await onboarder.onboard(did.did, did.verkey)

    await alice.post(
        "/wallet/did/public",
        params={
            "did": did.did,
            "mediation_id": alice_mediation_record.mediation_id,
        },
    )

    result = await alice.get(
        f"/resolver/resolve/did:sov:{did.did}", response=ResolutionResult
    )
    assert result.did_document["service"]
    assert (
        result.did_document["service"][0]["serviceEndpoint"] == "http://mediator:3000"
    )
    yield did


@pytest.mark.asyncio
async def test_public_did_endpoint_has_mediator_info(public_did_with_mediator: DID):
    """Test that a public DID will have mediator info if specified on registration."""
    assert public_did_with_mediator


@pytest.mark.asyncio
async def test_create_oob_invitation(alice: Controller, public_did_with_mediator: DID):
    """Test creationg of OOB invitation with public DID."""
    assert public_did_with_mediator
    await alice.post(
        "/out-of-band/create-invitation",
        json={
            "alias": "Barry",
            "handshake_protocols": [
                "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/didexchange/1.0"
            ],
            "metadata": {},
            "my_label": "Invitation to Barry",
            "use_public_did": True,
        },
    )
