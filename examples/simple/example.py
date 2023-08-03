"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv

from controller import Controller
from controller.logging import logging_to_stdout
from controller.protocols import didexchange

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        await didexchange(alice, bob)


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
