"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv

from controller import Controller
from controller.logging import logging_to_stdout
from controller.protocols import (
    didexchange,
    indy_anoncred_onboard,
    request_mediation_v1,
)

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")
MEDIATOR = getenv("MEDIATOR", "http://mediator:3001")


async def get_their_endpoint(agent: Controller, connection_id: str) -> str:
    endpoints = await agent.get(f"/connections/{connection_id}/endpoints")
    return endpoints["their_endpoint"]


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(
        base_url=BOB
    ) as bob, Controller(base_url=MEDIATOR) as mediator:
        public_did = await indy_anoncred_onboard(alice)
        ma_conn, am_conn = await didexchange(mediator, alice)
        _, mediation_record = await request_mediation_v1(
            mediator, alice, ma_conn.connection_id, am_conn.connection_id
        )
        await alice.put(f"/mediation/{mediation_record.mediation_id}/default-mediator")
        ab_conn, ba_conn = await didexchange(alice, bob, use_public_did=True)
        alice_endpoint = await get_their_endpoint(bob, ba_conn.connection_id)
        assert alice_endpoint == "http://mediator:3000"


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
