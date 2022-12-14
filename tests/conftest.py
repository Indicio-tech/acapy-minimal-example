from os import getenv
from secrets import token_hex
from typing import Tuple

from echo_agent.client import EchoClient
from echo_agent.models import ConnectionInfo
import pytest
import pytest_asyncio

from controller.controller import Controller
from controller.models import ConnectionStaticResult, MediationRecord


def getenv_or_raise(var: str) -> str:
    """Get env var or raise if absent."""
    value = getenv(var)
    if value is None:
        raise ValueError(f"Missing environmnet variable: {var}")

    return value


@pytest_asyncio.fixture
async def mediator():
    """Get mediator."""
    controller = await Controller(getenv_or_raise("MEDIATOR")).setup()
    yield controller
    await controller.shutdown()


@pytest_asyncio.fixture
async def echo():
    """Get echo client."""
    client = EchoClient(getenv_or_raise("ECHO"))
    async with client as session:
        yield session


@pytest_asyncio.fixture
async def agent():
    """Get agent."""
    agent = await Controller(getenv_or_raise("AGENT")).setup()
    async with agent as session:
        yield session
        await session.shutdown()


@pytest_asyncio.fixture
async def mediator_echo_connection(mediator: Controller, echo: EchoClient):
    """Connect mediator and echo agent."""
    agent_seed = token_hex(16)
    echo_seed = token_hex(16)
    mediator_conn = await mediator.post(
        "/connections/create-static",
        json={
            "my_seed": agent_seed,
            "their_seed": echo_seed,
            "their_label": "test-runner",
        },
        response=ConnectionStaticResult,
    )

    echo_conn = await echo.new_connection(
        seed=echo_seed,
        endpoint=mediator_conn.my_endpoint,
        recipient_keys=[mediator_conn.my_verkey],
    )
    yield mediator_conn, echo_conn


@pytest.fixture
def echo_connection_id(
    mediator_echo_connection: Tuple[ConnectionStaticResult, ConnectionInfo]
):
    """Get echo connection ID from mediator perspective."""
    mediator, _ = mediator_echo_connection
    yield mediator.record.connection_id


@pytest.fixture
def mediator_connection(
    mediator_echo_connection: Tuple[ConnectionStaticResult, ConnectionInfo]
):
    """Get mediator connection info from echo agent perspective."""
    _, echo = mediator_echo_connection
    yield echo


@pytest.fixture
def mediator_connection_id(
    mediator_echo_connection: Tuple[ConnectionStaticResult, ConnectionInfo]
):
    """Get mediator connection ID from echo agent perspective."""
    _, echo = mediator_echo_connection
    yield echo.connection_id


@pytest.fixture
def mediator_ws_endpoint():
    yield getenv_or_raise("MEDIATOR_WS")


@pytest_asyncio.fixture
async def mediation_granted(
    mediator: Controller,
    echo: EchoClient,
    mediator_connection: ConnectionInfo,
    echo_connection_id: str,
    mediator_ws_endpoint: str,
):
    """Mediation granted to echo agent."""
    async with echo.session(mediator_connection, mediator_ws_endpoint) as session:
        await echo.send_message_to_session(
            session,
            {
                "@type": "https://didcomm.org/coordinate-mediation/1.0/mediate-request",
                "~transport": {"return_route": "all"},
            },
        )
        mediation_record = await mediator.record_with_values(
            topic="mediation",
            connection_id=echo_connection_id,
            state="request",
            record_type=MediationRecord,
        )
        mediation_record = await mediator.record_with_values(
            topic="mediation",
            connection_id=echo_connection_id,
            state="granted",
            record_type=MediationRecord,
        )
        assert mediation_record
        grant = await echo.get_message(mediator_connection, session=session)
        assert "mediate-grant" in grant["@type"]
        yield grant
