"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.protocols import didexchange, oob_invitation

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        invite = await oob_invitation(alice, multi_use=True)
        a_conn, _ = await didexchange(alice, bob, invite=invite)
        result = await alice.get(
            "/discover-features/query", params={"connection_id": a_conn.connection_id}
        )
        print(result)


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
