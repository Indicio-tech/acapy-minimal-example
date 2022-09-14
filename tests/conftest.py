from os import getenv

import pytest
import pytest_asyncio
from controller.controller import Controller


def getenv_or_raise(var: str) -> str:
    value = getenv(var)
    if value is None:
        raise ValueError(f"Missing environmnet variable: {var}")

    return value


@pytest_asyncio.fixture
async def holder():
    controller = await Controller(getenv_or_raise("HOLDER")).setup()
    yield controller
    await controller.shutdown()


@pytest_asyncio.fixture
async def issuer():
    controller = await Controller(getenv_or_raise("ISSUER")).setup()
    yield controller
    await controller.shutdown()


@pytest.fixture
def verifier(issuer):
    yield issuer
