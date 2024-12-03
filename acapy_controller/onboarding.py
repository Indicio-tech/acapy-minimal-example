"""Functions for onboarding a DID to an Indy ledger.

This uses common "self-serve" tools for onboarding, such as those provided by
VON network images or the self-serve apps provided by Indicio for their
networks.
"""

from abc import ABC, abstractmethod
import json
import logging
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
INDICIO_DEMONET_GENESIS = (
    "https://raw.githubusercontent.com/Indicio-tech/indicio-network/main/"
    "genesis_files/pool_transactions_demonet_genesis"
)
LOGGER = logging.getLogger(__name__)


def get_onboarder(genesis_url: str) -> Optional["Onboarder"]:
    """Determine which onboarder to use based on genesis URL."""

    if genesis_url.endswith("/genesis"):
        # infer VonOnboarder
        return VonOnboarder(genesis_url.replace("/genesis", "/register"))

    return {
        INDICIO_TESTNET_GENESIS: SelfServeOnboarder(
            "https://selfserve.indiciotech.io/nym", "testnet"
        ),
        INDICIO_TESTNET_GENESIS_OLD: SelfServeOnboarder(
            "https://selfserve.indiciotech.io/nym", "testnet"
        ),
        INDICIO_DEMONET_GENESIS: SelfServeOnboarder(
            "https://selfserve.indiciotech.io/nym", "demonet"
        ),
    }.get(genesis_url)


class OnboardingError(Exception):
    """Error while onboarding."""


class Onboarder(ABC):
    """Abstract base class for onboarders."""

    @abstractmethod
    async def onboard(self, did: str, verkey: str):
        """Onboard a DID."""


class VonOnboarder(Onboarder):
    """Onboard a DID to a VON network."""

    def __init__(self, registration_url: str):
        """Initialize the onboarder."""
        self.registration_url = registration_url

    async def onboard(self, did: str, verkey: str):
        """Onboard a DID to a VON network."""

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
    """Onboard a DID to an Indicio network using self-serve."""

    def __init__(self, registration_url: str, network: str):
        """Initialize the onboarder."""
        self.registration_url = registration_url
        self.network = network

    async def onboard(self, did: str, verkey: str):
        """Onboard a DID to an Indicio network using self-serve."""

        LOGGER.debug(
            "Anchoring DID %s using self-serve on network: %s", did, self.network
        )
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
                else:
                    body = await resp.text()
                    raise OnboardingError(f"Failed to write DID: {resp.status}; {body}")
