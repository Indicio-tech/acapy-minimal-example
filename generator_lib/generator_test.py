import pytest
from .generator import Generator, ACAPYContainer

@pytest.fixture
def new_generator():
    return Generator()

def test_generator_generate(new_generator):
    assert new_generator.generate() == "hi"

def test_generator_create_acapy(new_generator):
    assert isinstance(new_generator.create_acapy(), ACAPYContainer)