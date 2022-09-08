"""Driver."""
import asyncio
from os import getenv

from aries_cloudcontroller import AcaPyClient

BASE_URL = getenv("AGENT_ENDPOINT", "http://localhost:3001")


async def main():
    """Driver test."""
    async with AcaPyClient(base_url=BASE_URL, admin_insecure=True) as agent:
        print((await agent.server.get_config()).json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
