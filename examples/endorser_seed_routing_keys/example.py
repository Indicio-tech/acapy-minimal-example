"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.protocols import (
    connection, 
    didexchange, 
    indy_anoncred_onboard,
    oob_invitation
)

AUTHOR = getenv("AUTHOR", "http://author:3001")
ENDORSER = getenv("ENDORSER", "http://endorser:3001")


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=AUTHOR) as author, Controller(base_url=ENDORSER) as endorser:
        # 1. Want to set up endorser with its seed (Alex)
        # (brb need to spin up agent with a seed to see which endpoint we can hit)
        with section("Grab DID and Verkey from Seed"): 
           print("GRABBING SEED INFORMATION")
           seed_information = await endorser.get("/wallet/did/public")
           print(seed_information)
           # Grab did and verkey
           
        with section("Onboard Endorser"):
            endorser_public_did = await indy_anoncred_onboard(endorser)

         # 2. Make OOB invitation from endorser to author (Athan) 
         # 3. Have author receive invitation (Athan)
          with section("Establish connection"):
            endorser_con, author_con = await didexchange(endorser, author) # Endorser creates invite for author
            # ^didexchange would work here

            # 4. Verify connection in active or done state (Athan)
                # this is not correct, surely? is there a built-in way to do logging or is this it?
            assert(endorser_con.rfc23_state == "completed" or endorser_con.rfc23_state == "done") 
            assert(author_con.rfc23_state == "completed" or author_con.rfc23_state == "done") 

            # 5. Down endorser, down author, respin them back up (Alex)
            # 6. Verify it's back up^ 
            # 7. Make OOB invitation from endorser to author (Athan) --> this shouldn't fail, but does
            endorser_con, author_con = await didexchange(endorser, author)
                # use-existing-connection = True?


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
