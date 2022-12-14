from time import sleep
from echo_agent.client import EchoClient
from echo_agent.models import ConnectionInfo
import pytest
from secrets import token_hex

from controller.controller import Controller
from controller.models import InvitationResult, MediationRecord


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
    mediation_granted: dict,
):
    """"""
    print(mediation_granted)
    print("\n")
    agent_seed = token_hex(16)
    echo_seed = token_hex(16)

    invitation = await agent.post(
        "/connections/create-invitation", json={}, response=InvitationResult
    )

    invite_conn = await echo.new_connection(
        seed=echo_seed,
        endpoint=invitation.invitation.service_endpoint,
        recipient_keys=invitation.invitation.dict()["recipient_keys"],
    )

    print(invite_conn)

    async with echo.session(mediator_connection, mediator_ws_endpoint) as session:
        await echo.send_message_to_session(
            session,
            {
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/coordinate-mediation/1.0/keylist-update",
                "updates": [
                    {
                        "recipient_key": invite_conn.verkey,
                        "action": "add",
                    }
                ],
                "~transport": {"return_route": "all"},
            },
        )

        keylist_response = await echo.get_message(
            connection=mediator_connection,
            msg_type="did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/coordinate-mediation/1.0/keylist-update-response",
            session=session,
        )

        print(keylist_response)

    request = {
        "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/request",
        "label": "Echo",
        "connection": {
            "DID": invite_conn.did,
            "DIDDoc": {
                "@context": "https://w3id.org/did/v1",
                "id": invite_conn.did,
                "publicKey": [
                    {
                        "id": f"did:sov:{invite_conn.did}#key-1",
                        "type": "Ed25519VerificationKey2018",
                        "controller": invite_conn.did,
                        "publicKeyBase58": invite_conn.verkey,
                    }
                ],
                "authentication": [
                    {
                        "publicKey": f"did:sov:{invite_conn.did}#key-1",
                        "type": "Ed25519SignatureAuthentication2018",
                    }
                ],
                "service": [
                    {
                        "id": f"did:sov:{invite_conn.did};didcomm",
                        "type": "IndyAgent",
                        "priority": 0,
                        "routingKeys": mediation_granted["routing_keys"],
                        "serviceEndpoint": mediation_granted["endpoint"],
                        "recipientKeys": [invite_conn.verkey],
                    }
                ],
            },
        },
    }

    await echo.send_message(
        connection=invite_conn,
        message=request,
    )

    async with echo.session(mediator_connection, mediator_ws_endpoint) as session:

        await echo.send_message_to_session(
            session=session,
            message={
                "@type": "https://didcomm.org/trust_ping/1.0/ping",
                "response_requested": "false",
                "~transport": {"return_route": "all"},
            },
        )
        # sleep(5)
        # foo = await echo.get_messages(mediator_connection, session=session)
        foo = await echo.get_message(connection=invite_conn, session=session)
        print(foo)

    assert False
