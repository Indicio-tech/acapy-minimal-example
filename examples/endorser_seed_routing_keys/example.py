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
    oob_invitation
)
import httpx

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
           print("DID: ", seed_information["result"]["did"])
           endorser_did = seed_information["result"]["did"]
           print("Verkey: ", seed_information["result"]["verkey"])
           endorser_verkey = seed_information["result"]["verkey"]
           print(seed_information)
           # Grab did and verkey

        
           
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

            # Endorser creates schema
            schema, cred_def = await indy_anoncred_credential_artifacts(
                endorser,
                ["firstname", "lastname"],
                support_revocation=True,
            )
            print("DID WE DO A THING?")
            print("Schemay: ", schema)

        # Attempt to create schema to see if it works

         # 2. Make OOB invitation from endorser to author (Athan) 
         # 3. Have author receive invitation (Athan)
        with section("Establish connection"):
          endorser_conn, author_conn = await didexchange(endorser, author) # Endorser creates invite for author
          # ^didexchange would work here
          print("what information do we have to work with")
          print("endorser_conn")
          print(endorser_conn)
          print("author_conn")
          print(author_conn)

          # 4. Verify connection in active or done state (Athan)
              # this is not correct, surely? is there a built-in way to do logging or is this it?
          # assert(endorser_con.rfc23_state == "completed" or endorser_con.rfc23_state == "done") 
          # assert(author_con.rfc23_state == "completed" or author_con.rfc23_state == "done") 

          # 5. Down endorser, down author, respin them back up (Alex)
          # 6. Verify it's back up^ 
          # 7. Make OOB invitation from endorser to author (Athan) --> this shouldn't fail, but does
          # endorser_con, author_con = await didexchange(endorser, author)
              # use-existing-connection = True?


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
