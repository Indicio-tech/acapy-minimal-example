"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
import logging
from os import getenv

from acapy_controller import Controller
from acapy_controller.controller import ControllerError, Minimal
from acapy_controller.logging import logging_to_stdout, section
from acapy_controller.models import CreateWalletResponse, DIDResult
from acapy_controller.protocols import (
    didexchange,
    indy_anoncred_credential_artifacts,
    indy_anoncred_onboard,
    oob_invitation,
    ConnRecord,
)

AGENCY = getenv("AGENCY", "http://agency:3001")


@dataclass()
class EndorseTxn(Minimal):
    """Endorse txn request."""

    transaction_id: str
    state: str


async def indy_anoncred_onboard_via_endorser(
    endorser: Controller,
    issuer: Controller,
) -> tuple[str, ConnRecord, ConnRecord]:
    """Do onboarding via endorser."""
    endo_did = await indy_anoncred_onboard(endorser)
    pub_invite = await oob_invitation(endorser, use_public_did=True)

    # ea - endorser to issuer conn
    # ae- issuer to endorser conn
    ea, ae = await didexchange(endorser, issuer, invite=pub_invite)

    # Trigger endorser set role
    await endorser.post(
        f"/transactions/{ea.connection_id}/set-endorser-role",
        params={"transaction_my_job": "TRANSACTION_ENDORSER"},
    )
    await issuer.post(
        f"/transactions/{ae.connection_id}/set-endorser-role",
        params={"transaction_my_job": "TRANSACTION_AUTHOR"},
    )

    # Set endorser info
    await issuer.put(
        "/settings",
        json={
            "extra_settings": {
                "endorser-protocol-role": "author",
                "auto-request-endorsement": True,
                "auto-write-transactions": True,
                "auto-create-revocation-transactions": True,
            }
        },
    )
    assert ae.their_public_did
    assert ae.their_public_did == endo_did.did
    await issuer.post(
        f"/transactions/{ae.connection_id}/set-endorser-info",
        params={"endorser_did": ae.their_public_did},
    )

    # Register nym for issuer/issuer
    result = await issuer.post(
        "/wallet/did/create",
        json={
            "method": "sov",
            "options": {
                "key_type": "ed25519",
            },
        },
        response=DIDResult,
    )
    assert result.result
    issuer_did = result.result

    await issuer.post(
        "/ledger/register-nym",
        params={
            "did": issuer_did.did,
            "verkey": issuer_did.verkey,
            "conn_id": ae.connection_id,
            "create_transaction_for_endorser": "true",
        },
    )

    txn = await endorser.event_with_values(
        "endorse_transaction", state="request_received", event_type=EndorseTxn
    )
    await endorser.post(f"/transactions/{txn.transaction_id}/endorse")
    await issuer.event_with_values("endorse_transaction", state="transaction_acked")

    config = (await issuer.get("/status/config"))["config"]
    genesis_url = config.get("ledger.genesis_url")

    if not genesis_url:
        raise ControllerError("No ledger configured on agent")

    taa = (await issuer.get("/ledger/taa"))["result"]
    if taa.get("taa_required") is True and taa.get("taa_accepted") is None:
        await issuer.post(
            "/ledger/taa/accept",
            json={
                "mechanism": "on_file",
                "text": taa["taa_record"]["text"],
                "version": taa["taa_record"]["version"],
            },
        )
    await issuer.post(
        "/wallet/did/public",
        params={
            "did": issuer_did.did,
            "conn_id": ae.connection_id,
        },
    )
    txn = await endorser.event_with_values(
        "endorse_transaction", state="request_received", event_type=EndorseTxn
    )
    await endorser.post(f"/transactions/{txn.transaction_id}/endorse")
    await issuer.event_with_values("endorse_transaction", state="transaction_acked")

    endorser.event_queue.flush()
    issuer.event_queue.flush()

    return issuer_did.did, ea, ae


LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def auto_endorse_all(endorser: Controller):
    """Auto endorse all received requests."""

    async def _inner():
        while True:
            LOGGER.debug("Looking for endorse requests...")
            try:
                txn = await endorser.event_with_values(
                    "endorse_transaction",
                    state="request_received",
                    event_type=EndorseTxn,
                )
                LOGGER.debug("Request received: %s", txn)
                await endorser.post(f"/transactions/{txn.transaction_id}/endorse")
            except TimeoutError:
                LOGGER.debug("Timeout while waiting for endorse request")
            except Exception:
                LOGGER.exception("Something went wrong in auto endorse loop")

    task = asyncio.create_task(_inner())

    yield

    task.cancel()
    with suppress(asyncio.CancelledError, TimeoutError):
        await task


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=AGENCY) as agency:
        alice = await agency.post(
            "/multitenancy/wallet",
            json={
                "label": "Alice",
                "wallet_type": "askar-anoncreds",
            },
            response=CreateWalletResponse,
        )
        bob = await agency.post(
            "/multitenancy/wallet",
            json={
                "label": "Bob",
                "wallet_type": "askar-anoncreds",
            },
            response=CreateWalletResponse,
        )

    async with (
        Controller(
            base_url=AGENCY, wallet_id=alice.wallet_id, subwallet_token=alice.token
        ) as alice,
        Controller(
            base_url=AGENCY, wallet_id=bob.wallet_id, subwallet_token=bob.token
        ) as bob,
    ):
        # Issuance prep
        await indy_anoncred_onboard(bob)
        alice_did, _, alice_conn = await indy_anoncred_onboard_via_endorser(bob, alice)

        with section("AnonCreds artifact registration"):
            async with auto_endorse_all(bob):
                _, cred_def = await indy_anoncred_credential_artifacts(
                    alice,
                    ["firstname", "lastname"],
                    support_revocation=True,
                    issuer_id=alice_did,
                    endorser_connection_id=alice_conn.connection_id,
                )


if __name__ == "__main__":
    logging_to_stdout(LOGGER)
    asyncio.run(main())
