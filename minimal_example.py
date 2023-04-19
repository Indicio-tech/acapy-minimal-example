"""Minimal reproducible example script.
This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
import json
from os import getenv

from controller import Controller
from controller.logging import logging_to_stdout
from controller.models import (
    IndyPresPreview,
    V10PresentationExchange,
    V10PresentationExchangeList,
    V10PresentationProposalRequest,
    V10PresentationSendRequestToProposal,
)
from controller.protocols import (
    didexchange,
)

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")


def summary(presentation: V10PresentationExchange) -> str:
    return "Summary: " + json.dumps(
        {
            "state": presentation.state,
            "verified": presentation.verified,
            "presentation_request": presentation.presentation_request.dict(
                by_alias=True
            )
            if presentation.presentation_request
            else None,
            "presentation": presentation.presentation.dict(by_alias=True)
            if presentation.presentation
            else None,
        },
        indent=2,
        sort_keys=True,
    )


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        # Connecting
        alice_conn, bob_conn = await didexchange(alice, bob)

        # Present the thing
        bob_pres_ex = await bob.post(
            "/present-proof/send-proposal",
            json=V10PresentationProposalRequest(
                auto_present=False,
                comment="Presentation proposal from minimal",
                connection_id=bob_conn.connection_id,
                presentation_proposal=IndyPresPreview.parse_obj(
                    {
                        "@type": "https://didcomm.org/present-proof/"
                        "1.0/presentation-preview",
                        "attributes": [
                            {
                                "name": "dtc",
                                "value": "fake dtc value",
                            }
                        ],
                        "predicates": [],
                    }
                ),
                trace=False,
            ),
        )
        alice_pres_id = await alice.record_with_values(
            topic="present_proof",
            record_type=V10PresentationExchange,
            connection_id=alice_conn.connection_id,
            state="proposal_received",
        )
        alice_pres_ex = await alice.post(
            "/present-proof/records/"
            f"{alice_pres_id.presentation_exchange_id}/send-request",
            json=V10PresentationSendRequestToProposal(
                auto_verify=False,
                trace=False,
            ),
            response=V10PresentationExchange,
        )
        alice_pres_ex_id = alice_pres_ex.presentation_exchange_id

        bob_pres_ex = await bob.record_with_values(
            topic="present_proof",
            record_type=V10PresentationExchange,
            connection_id=bob_conn.connection_id,
            state="request_received",
        )
        assert bob_pres_ex.presentation_request
        bob_pres_ex_id = bob_pres_ex.presentation_exchange_id

        bob_pres_ex = await bob.post(
            f"/present-proof/records/{bob_pres_ex_id}/send-presentation",
            json={
                "requested_attributes": {},
                "requested_predicates": {},
                "self_attested_attributes": {"self_dtc_uuid": "dtc data goes here"},
            },
            response=V10PresentationExchange,
        )

        await alice.record_with_values(
            topic="present_proof",
            record_type=V10PresentationExchange,
            presentation_exchange_id=alice_pres_ex_id,
            state="presentation_received",
        )
        alice_pres_ex = await alice.post(
            f"/present-proof/records/{alice_pres_ex_id}/verify-presentation",
            json={},
            response=V10PresentationExchange,
        )
        alice_pres_ex = await alice.record_with_values(
            topic="present_proof",
            record_type=V10PresentationExchange,
            presentation_exchange_id=alice_pres_ex_id,
            state="verified",
        )

        bob_pres_ex = await bob.record_with_values(
            topic="present_proof",
            record_type=V10PresentationExchange,
            presentation_exchange_id=bob_pres_ex_id,
            state="presentation_acked",
        )

        print(alice_pres_ex.json(by_alias=True, indent=2))
        presentations = await alice.get(
            "/present-proof/records", response=V10PresentationExchangeList
        )

        # Presentation summary
        for pres in presentations.results or []:
            print(summary(pres))
        return presentations


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
