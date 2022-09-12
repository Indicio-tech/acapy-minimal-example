from os import getenv

import pytest
from controller.controller import Controller


def getenv_or_raise(var: str) -> str:
    value = getenv(var)
    if value is None:
        raise ValueError(f"Missing environmnet variable: {var}")

    return value


@pytest.fixture
def holder():
    yield Controller(getenv_or_raise("HOLDER"))


@pytest.fixture
def issuer():
    yield Controller(getenv_or_raise("ISSUER"))


@pytest.fixture
def verifier(issuer):
    yield issuer
