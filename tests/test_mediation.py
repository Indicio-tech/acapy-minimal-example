from echo_agent.client import EchoClient
from echo_agent.models import ConnectionInfo
import pytest
from secrets import token_hex

from controller.controller import Controller
from controller.models import InvitationResult


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
                "@type": "https://didcomm.org/trust_ping/1.0/ping",
                "response_requested": "true",
            },
        )

        await echo.send_message_to_session(
            session,
            {
                "@type": "https://didcomm.org/trust_ping/1.0/ping",
                "response_requested": "false",
                "transport": {"return_route": "all"},
            },
        )

        response = await echo.get_message(mediator_connection, session=session)
        assert "ping_response" in response["@type"]


@pytest.mark.asyncio
async def test_with_agent(
    agent: Controller,
    echo: EchoClient,
    mediator_connection: ConnectionInfo,
    mediator_ws_endpoint: str,
):
    """"""

    agent_seed = token_hex(16)
    echo_seed = token_hex(16)

    invitation = await agent.post(
        "/connections/create-invitation", json={}, response=InvitationResult
    )

    echo.new_connection(seed=echo_seed, endpoint=invitation.invitation.service_endpoint)

    print(invitation)

    async with echo.session(mediator_connection, mediator_ws_endpoint) as session:
        await echo.send_message_to_session(
            session,
            {
                "@type": "/https://didcomm.org/coordinate-mediation/1.0/keylist-update",
                "updates": [
                    {
                        "recipient_key": "",
                        "action": "add",
                    }
                ],
            },
        )

    assert False
