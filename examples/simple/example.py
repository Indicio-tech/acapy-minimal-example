"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv

from controller import Controller
from controller.logging import logging_to_stdout
from controller.protocols import didexchange, oob_invitation

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        invite = await oob_invitation(alice, multi_use=True)
        alice_conn, bob_conn = await didexchange(alice, bob, invite=invite)


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
