"""Driver."""
import asyncio
from os import getenv

from .controller import Controller
from .models import DIDCreate, DIDCreateOptions, DIDResult
from .logging import logging_to_stdout

BASE_URL = getenv("AGENT_ENDPOINT", "http://localhost:3001")


async def main():
    """Driver test."""
    agent = await Controller(base_url=BASE_URL).setup()
    print(await agent.get("/status/config"))
    print(
        await agent.post(
            "/wallet/did/create",
            json=DIDCreate(
                method="sov", options=DIDCreateOptions(key_type="ed25519")
            ),
            as_type=DIDResult,
        )
    )


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
