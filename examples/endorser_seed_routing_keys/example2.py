"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv

from acapy_controller.controller import Controller
from acapy_controller.logging import logging_to_stdout, section
from acapy_controller.protocols import (
    didexchange,
    indy_anoncred_onboard,
    oob_invitation,
)

AUTHOR = getenv("AUTHOR", "http://author:3001")
ENDORSER = getenv("ENDORSER", "http://endorser:3001")


async def main():
    """Perform part 2 of the test.

    The endorser will have been stopped, its data cleared.
    We then try to form a new connection with the author and endorser through
    the endorser's public DID, which will "persist" because the --seed flag was
    used.

    If all goes well, the endorser and author will connect.
    To reproduce an issue we're seeing in another context, we would expect this
    to fail because the routing keys of the endorser's mediator haven't been
    updated on the network.
    """
    async with (
        Controller(base_url=AUTHOR) as author,
        Controller(base_url=ENDORSER) as endorser,
    ):
        with section("Update endpoint info"):
            did_info = await indy_anoncred_onboard(endorser)
            await endorser.post(
                "/wallet/set-did-endpoint",
                json={
                    "did": did_info.did,
                },
            )

        with section("Establish connection"):
            endorser_oob_invite = await oob_invitation(
                endorser, use_public_did=True, multi_use=False
            )
            await didexchange(endorser, author, invite=endorser_oob_invite)


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
