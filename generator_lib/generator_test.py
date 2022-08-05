import pytest
from .generator import Generator

@pytest.fixture
def new_generator():
	return Generator()

def test_generator_generate(new_generator):
	assert new_generator.generate() == "hi"