import pytest
from .generator import Generator, DockerConfig, ACAPYContainer


@pytest.fixture
def new_generator():
    return Generator()


@pytest.fixture
def new_dockerconfig():
    return DockerConfig()


def test_generator_generate(new_generator):
    assert new_generator.generate() == "hi"


def test_generator_create_acapy(new_generator):
    assert isinstance(new_generator.create_acapy(), ACAPYContainer)


def test_dockerconfig_generate(new_dockerconfig):
    print(new_dockerconfig.generate())
