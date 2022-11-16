from os import getenv

import pytest_asyncio
from controller.controller import Controller


def getenv_or_raise(var: str) -> str:
    value = getenv(var)
    if value is None:
        raise ValueError(f"Missing environmnet variable: {var}")

    return value


@pytest_asyncio.fixture
async def alice():
    controller = await Controller(getenv_or_raise("ALICE")).setup()
    yield controller
    await controller.shutdown()


@pytest_asyncio.fixture
async def bob():
    controller = await Controller(getenv_or_raise("BOB")).setup()
    yield controller
    await controller.shutdown()
