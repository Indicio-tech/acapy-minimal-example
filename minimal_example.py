"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from datetime import date
from os import getenv
from uuid import uuid4

from controller import Controller
from controller.logging import logging_to_stdout
from controller.models import DIDResult
from controller.protocols import (
    connection,
    didexchange,
    indy_anoncred_onboard,
    jsonld_issue_credential,
    jsonld_present_proof,
)

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://alice:3001")


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        await connection(alice, bob)
        alice_conn, bob_conn = await didexchange(alice, bob)
        public_did = await indy_anoncred_onboard(alice)
        bob_did = (
            await bob.post(
                "/wallet/did/create",
                json={"method": "key", "options": {"key_type": "ed25519"}},
                response=DIDResult,
            )
        ).result
        assert bob_did

        issuer_cred_ex, holder_cred_ex = await jsonld_issue_credential(
            alice,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            credential={
                "@context": [
                    "https://www.w3.org/2018/credentials/v1",
                    "https://w3id.org/citizenship/v1",
                ],
                "type": ["VerifiableCredential", "PermanentResident"],
                "issuer": "did:sov:" + public_did.did,
                "issuanceDate": str(date.today()),
                "credentialSubject": {
                    "type": ["PermanentResident"],
                    "id": bob_did.did,
                    "givenName": "Bob",
                    "familyName": "Builder",
                    "gender": "Female",
                    "birthCountry": "Bahamas",
                    "birthDate": "1958-07-17",
                },
            },
            options={"proofType": "Ed25519Signature2018"},
        )
        alice_pres_ex, bob_pres_ex = await jsonld_present_proof(
            alice,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            presentation_definition={
                "input_descriptors": [
                    {
                        "id": "citizenship_input_1",
                        "name": "EU Driver's License",
                        "schema": [
                            {
                                "uri": "https://www.w3.org/2018/credentials#VerifiableCredential"  # noqa: E501
                            },
                            {"uri": "https://w3id.org/citizenship#PermanentResident"},
                        ],
                        "constraints": {
                            "is_holder": [
                                {
                                    "directive": "required",
                                    "field_id": [
                                        "1f44d55f-f161-4938-a659-f8026467f126"
                                    ],
                                }
                            ],
                            "fields": [
                                {
                                    "id": "1f44d55f-f161-4938-a659-f8026467f126",
                                    "path": ["$.credentialSubject.familyName"],
                                    "purpose": "The claim must be from one of the specified issuers",  # noqa: E501
                                    "filter": {"const": "Builder"},
                                },
                                {
                                    "path": ["$.credentialSubject.givenName"],
                                    "purpose": "The claim must be from one of the specified issuers",  # noqa: E501
                                },
                            ],
                        },
                    }
                ],
                "id": str(uuid4()),
                "format": {"ldp_vp": {"proof_type": ["Ed25519Signature2018"]}},
            },
            domain="test-degree",
        )
        print(alice_pres_ex.json(by_alias=True, indent=2))


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
