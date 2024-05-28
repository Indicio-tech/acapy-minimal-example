"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.models import CreateWalletResponse
from acapy_controller.protocols import (
    didexchange,
    indy_anoncred_credential_artifacts,
    indy_anoncred_onboard,
    indy_issue_credential_v2,
    indy_present_proof_v2,
)

AGENCY = getenv("AGENCY", "http://agency:3001")


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=AGENCY) as agency:
        alice = await agency.post(
            "/multitenancy/wallet",
            json={
                "label": "Alice",
                "wallet_type": "askar",
            },
            response=CreateWalletResponse,
        )
        bob = await agency.post(
            "/multitenancy/wallet",
            json={
                "label": "Bob",
                "wallet_type": "askar",
            },
            response=CreateWalletResponse,
        )

    async with Controller(
        base_url=AGENCY, wallet_id=alice.wallet_id, subwallet_token=alice.token
    ) as alice, Controller(
        base_url=AGENCY, wallet_id=bob.wallet_id, subwallet_token=bob.token
    ) as bob:
        # Issuance prep
        await indy_anoncred_onboard(alice)
        _, cred_def = await indy_anoncred_credential_artifacts(
            alice,
            ["firstname", "lastname"],
            support_revocation=True,
        )

        # Connecting
        alice_conn, bob_conn = await didexchange(alice, bob)

        # Issue a credential
        await indy_issue_credential_v2(
            alice,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            cred_def.credential_definition_id,
            {"firstname": "Bob", "lastname": "Builder"},
        )

        # Present the the credential's attributes
        await indy_present_proof_v2(
            bob,
            alice,
            bob_conn.connection_id,
            alice_conn.connection_id,
            requested_attributes=[{"name": "firstname"}],
        )


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
