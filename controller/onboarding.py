from abc import ABC, abstractmethod
import json
from typing import Optional
from aiohttp import ClientSession

INDICIO_TESTNET_GENESIS = (
    "https://raw.githubusercontent.com/Indicio-tech/indicio-network/main/"
    "genesis_files/pool_transactions_testnet_genesis"
)
INDICIO_TESTNET_GENESIS_OLD = (
    "https://raw.githubusercontent.com/Indicio-tech/indicio-network/master/"
    "genesis_files/pool_transactions_testnet_genesis"
)


def get_onboarder(genesis_url: str) -> Optional["Onboarder"]:
    if genesis_url.endswith("/genesis"):
        # infer VonOnboarder
        return VonOnboarder(genesis_url.replace("/genesis", "register"))

    return {
        INDICIO_TESTNET_GENESIS: SelfServeOnboarder(
            "https://selfserve.indiciotech.io/nym", "testnet"
        ),
        INDICIO_TESTNET_GENESIS_OLD: SelfServeOnboarder(
            "https://selfserve.indiciotech.io/nym", "testnet"
        ),
    }.get(genesis_url)


class Onboarder(ABC):
    @abstractmethod
    async def onboard(self, did: str, verkey: str):
        """Onboard a DID"""


class VonOnboarder(Onboarder):
    def __init__(self, registration_url: str):
        self.registration_url = registration_url

    async def onboard(self, did: str, verkey: str):
        async with ClientSession() as session:
            async with session.post(
                self.registration_url,
                json={
                    "did": did,
                    "verkey": verkey,
                    "alias": None,
                    "role": "ENDORSER",
                },
            ) as resp:
                if resp.ok:
                    return await resp.json()


class SelfServeOnboarder(Onboarder):
    def __init__(self, registration_url: str, network: str):
        self.registration_url = registration_url
        self.network = network

    async def onboard(self, did: str, verkey: str):
        async with ClientSession() as session:
            async with session.post(
                self.registration_url,
                headers={"content-type": "application/json; charset=utf-8"},
                json={
                    "network": self.network,
                    "did": did,
                    "verkey": verkey,
                    "alias": None,
                    "role": "ENDORSER",
                },
            ) as resp:
                if resp.ok:
                    body = await resp.text()
                    try:
                        return json.loads(body)
                    except json.decoder.JSONDecodeError:
                        return None
