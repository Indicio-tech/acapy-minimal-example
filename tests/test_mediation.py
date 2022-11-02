from echo_agent.client import EchoClient
from echo_agent.models import ConnectionInfo
import pytest

from controller.controller import Controller


@pytest.mark.asyncio
async def test_mediation_established(mediation_granted):
    pass


@pytest.mark.asyncio
async def test_trustping(
    mediator: Controller,
    echo: EchoClient,
    mediator_connection: ConnectionInfo,
    mediator_ws_endpoint: str,
):
    async with echo.session(mediator_connection, mediator_ws_endpoint) as session:
        await echo.send_message_to_session(
            session,
            {
                "@type": "https://didcomm.org/trustping/1.0/ping",
                "response_requested": "true",
                "~transport": {"return_route": "all"},
            },
        )
        response = await echo.get_message(mediator_connection, session=session)
        assert "ping_response" in response["@type"]
