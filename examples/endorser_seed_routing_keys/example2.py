"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv

from acapy_controller.controller import Controller, ControllerError, params
from acapy_controller.logging import logging_to_stdout, section
from acapy_controller.protocols import (
    connection, 
    didexchange, 
    indy_anoncred_credential_artifacts,
    indy_anoncred_onboard,
    oob_invitation,
    trustping
)
import httpx
from httpx import RequestError

AUTHOR = getenv("AUTHOR", "http://author:3001")
ENDORSER = getenv("ENDORSER", "http://endorser:3001")

async def main():
    """Test Controller protocols."""
    async with Controller(base_url=AUTHOR) as author, Controller(base_url=ENDORSER) as endorser:
        # 1. Want to set up endorser with its seed (Alex)
        # (brb need to spin up agent with a seed to see which endpoint we can hit)

         # 2. Make OOB invitation from endorser to author (Athan) 
         # 3. Have author receive invitation (Athan)
        with section("Establish connection"):
          endorser_oob_invite = await oob_invitation(endorser, use_public_did=True, multi_use=False)
          if (endorser_oob_invite):
            endorser_conn, author_conn = await didexchange(endorser, author, invite=endorser_oob_invite) # Endorser creates invite for author
            # ^didexchange would work here

            # 4. Verify connection in active or done state (Athan)
            assert(endorser_conn.rfc23_state == "completed")


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())