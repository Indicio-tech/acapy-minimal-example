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
        with section("Grab DID and Verkey from Seed"): 
           seed_information = await endorser.get("/wallet/did/public")
           endorser_did = seed_information["result"]["did"]
           endorser_verkey = seed_information["result"]["verkey"]

        with section("Onboard Endorser"):
            with section("Accept TAA"):
                config = (await endorser.get("/status/config"))["config"]
                genesis_url = config.get("ledger.genesis_url")

                if not genesis_url:
                    raise ControllerError("No ledger configured on endorser")

                taa = (await endorser.get("/ledger/taa"))["result"]
                if taa.get("taa_required") is True and taa.get("taa_accepted") is None:
                    await endorser.post(
                        "/ledger/taa/accept",
                        json={
                            "mechanism": "on_file",
                            "text": taa["taa_record"]["text"],
                            "version": taa["taa_record"]["version"],
                        },
                    )

            with section("Anchor Endorser DID"):
                print("Publishing DID through https://selfserve.indiciotech.io")
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            url="https://selfserve.indiciotech.io/nym",
                            json={
                                "network": "testnet",
                                "did": endorser_did,
                                "verkey": endorser_verkey,
                            },
                            timeout=30,
                        )
                        response.raise_for_status()  # Raise an exception for HTTP errors
                except httpx.HTTPStatusError as e:
                    print(f"HTTP error occurred: {e}")
                except Exception as e:
                    print(f"An error occurred: {e}")
                    return
                print("DID Published")

                await endorser.post("/wallet/did/public", params=params(did=endorser_did, verkey=endorser_verkey))

         # 2. Make OOB invitation from endorser to author (Athan) 
         # 3. Have author receive invitation (Athan)
        with section("Establish connection"):
          endorser_conn, author_conn = await didexchange(endorser, author) # Endorser creates invite for author
          # ^didexchange would work here

          # 4. Verify connection in active or done state (Athan)
          assert(endorser_conn.rfc23_state == "completed")

        #   # 5. Down endorser, down author, respin them back up (Alex)
        # with section("Down agents"):
        #     await endorser.get("/shutdown")

        #     await asyncio.sleep(10)

        #      # 5b. Can we ping? If not, yay!
        #     print("use endorser")
        #     max_retries = 10
        #     for attempt in range(max_retries):
        #         try:
        #             response = await trustping(endorser, endorser_conn)
        #             print(response)
        #             response.raise_for_status()
        #             print("Shutdown successful")
        #             return
        #         except RequestError as exc:
        #             print(f"Attempt {attempt + 1} failed: {exc}")
        #             if attempt < max_retries - 1:
        #                 await asyncio.sleep(2 ** attempt)  # Exponential backoff
        #             else:
        #                 print("Max retries reached. Could not shutdown the agent.")
        #                 raise
            
        #     print("use author")
        #     await trustping(author, author_conn)

        #     # 6. Verify it's back up^ 
        #     print("use endorser")
        #     await trustping(endorser, endorser_conn)
        #     print("use author")
        #     await trustping(author, author_conn)
        #     # 6b. Can we ping? If so, yay!

        #     # 7. Make OOB invitation from endorser to author (Athan) --> this shouldn't fail, but does
        #     # endorser_con, author_con = await didexchange(endorser, author)
        #         # use-existing-connection = True?


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
