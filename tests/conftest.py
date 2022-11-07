import asyncio
from os import getenv

import pytest
import pytest_asyncio
from controller.controller import Controller


def getenv_or_raise(var: str) -> str:
    value = getenv(var)
    if value is None:
        raise ValueError(f"Missing environmnet variable: {var}")

    return value


@pytest.fixture(scope="session")
def event_loop():
    """Get session scoped event."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def endorser():
    controller = await Controller(getenv_or_raise("ENDORSER")).setup()
    yield controller
    await controller.shutdown()


@pytest_asyncio.fixture(scope="session")
async def alice():
    controller = await Controller(getenv_or_raise("ALICE")).setup()
    yield controller
    await controller.shutdown()


@pytest_asyncio.fixture(scope="session")
async def bob():
    controller = await Controller(getenv_or_raise("BOB")).setup()
    yield controller
    await controller.shutdown()
