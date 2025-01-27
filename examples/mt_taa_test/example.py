"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.models import CreateWalletResponse

ACAPY = getenv("ACAPY", "http://acapy:3001")


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ACAPY) as acapy:
        alice = await acapy.post(
            "/multitenancy/wallet",
            json={
                "label": "Alice",
                "wallet_type": "askar",
            },
            response=CreateWalletResponse,
        )

    async with Controller(
        base_url=ACAPY, wallet_id=alice.wallet_id, subwallet_token=alice.token
    ) as alice:
        taa = (await alice.get("/ledger/taa"))["result"]
        if taa.get("taa_required") is True and taa.get("taa_accepted") is None:
            await alice.post(
                "/ledger/taa/accept",
                json={
                    "mechanism": "on_file",
                    "text": taa["taa_record"]["text"],
                    "version": taa["taa_record"]["version"],
                },
            )

    async with Controller(base_url=ACAPY) as acapy:
        bob = await acapy.post(
            "/multitenancy/wallet",
            json={
                "label": "Bob",
                "wallet_type": "askar",
            },
            response=CreateWalletResponse,
        )

    # await asyncio.sleep(700)

    async with Controller(
        base_url=ACAPY, wallet_id=bob.wallet_id, subwallet_token=bob.token
    ) as bob:
        taa = (await bob.get("/ledger/taa"))["result"]["taa_accepted"]
        print(taa)


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
