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
    """Perform step one of the setup.

    The endorser is onboarded and then a connection is formed through the public
    did between the endorser and the author.
    """
    async with (
        Controller(base_url=AUTHOR) as author,
        Controller(base_url=ENDORSER) as endorser,
    ):
        with section("Onboard Endorser"):
            await indy_anoncred_onboard(endorser, did_from_seed=True)

        with section("Establish connection"):
            endorser_oob_invite = await oob_invitation(
                endorser, use_public_did=True, multi_use=False
            )
            await didexchange(
                endorser, author, invite=endorser_oob_invite
            )


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
