"""Event Listener."""
import asyncio
from contextlib import asynccontextmanager, suppress
import json
import logging
from typing import Any, AsyncIterator, Mapping, Optional

from aiohttp import ClientSession, WSMsgType
from async_selective_queue import AsyncSelectiveQueue as Queue
from attr import dataclass

LOGGER = logging.getLogger(__name__)


@dataclass
class Event:
    """Event data class."""

    topic: str
    payload: Mapping[str, Any]
    wallet_id: Optional[str] = None


@dataclass
class EventQueueConfig:
    """Config for EventQueue."""

    label: str
    url: str
    wallet_id: Optional[str] = None

    @property
    def is_subwallet(self) -> bool:
        return self.wallet_id is not None


@asynccontextmanager
async def EventQueue(config: EventQueueConfig) -> AsyncIterator[Queue[Event]]:
    """Create event queue."""
    event_queue: Queue[Event] = Queue()
    ws_task = asyncio.get_event_loop().create_task(ws(config, event_queue))

    yield event_queue

    ws_task.cancel()
    with suppress(asyncio.CancelledError):
        await ws_task
    ws_task = None


async def _handle_message(
    config: EventQueueConfig, queue: Queue[Event], data: Mapping[str, Any]
):
    if data.get("topic") == "ping":
        LOGGER.debug("%s: WS Ping received", config.label)
        return

    try:
        event = Event(**data)
    except Exception:
        LOGGER.warning(
            "Unable to parse event: %s",
            json.dumps(data, indent=2),
        )
        return

    if event.topic == "settings":
        LOGGER.debug("Received settings for %s: %s", config.label, event)
        await queue.put(event)
        return

    if not config.is_subwallet or event.wallet_id == config.wallet_id:
        LOGGER.debug("%s: %s", config.label, event)
        await queue.put(event)


async def ws(config: EventQueueConfig, queue: Queue[Event]):
    """WS Task."""
    LOGGER.info("Opening WS to %s", config.url)
    async with ClientSession() as session:
        async with session.ws_connect(config.url, timeout=30.0) as ws:
            try:
                async for msg in ws:
                    if msg.type == WSMsgType.TEXT:
                        data = msg.json()
                        await _handle_message(config, queue, data)
                    if msg.type == WSMsgType.ERROR:
                        # TODO Can we continue after ERROR?
                        break
            finally:
                if not ws.closed:
                    await ws.close()
