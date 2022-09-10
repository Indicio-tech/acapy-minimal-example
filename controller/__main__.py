"""Driver."""
import asyncio
from os import getenv

from .controller import Controller
from .logging import logging_to_stdout
from .protocols import connection, didexchange, indy_anoncred_onboard

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://alice:3001")


async def main():
    """Driver test."""
    alice = await Controller(base_url=ALICE).setup()
    bob = await Controller(base_url=BOB).setup()

    print(await connection(alice, bob))
    print(await didexchange(alice, bob))
    await indy_anoncred_onboard(alice)


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
