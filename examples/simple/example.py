"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

from os import getenv

from controller import Controller
from controller.protocols import didexchange

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        await didexchange(alice, bob)
