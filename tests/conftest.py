from os import getenv

import pytest
import pytest_asyncio
from controller.controller import Controller
from uuid import uuid4
from datetime import datetime
import base64


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


@pytest.fixture
def attributes() -> dict:
    attributes = {
        "firstname": "Bob",
        "lastname": "Builder",
        "age": "42",
        "image": "hl:zQmWvQxTqbG2Z9HPJgG57jjwR154cKhbtJenbyYTWkjgF3e",
    }
    yield attributes


@pytest.fixture
def supplement() -> dict:
    attachment_id = str(uuid4())
    supplement = {
        "type": "hashlink-data",
        "ref": attachment_id,
        "attrs": [{"key": "field", "value": "image"}],
    }
    yield supplement


@pytest.fixture
def attachment(supplement: dict) -> dict:
    data = b"Hello World!"
    attachment = {
        "@id": supplement["ref"],
        "mime-type": "image/jpeg",
        "filename": "face.png",
        "byte_count": len(data),
        "lastmod_time": str(datetime.now()),
        "description": "A picture of a face",
        "data": {"base64": base64.urlsafe_b64encode(data).decode()},
    }
    yield attachment
