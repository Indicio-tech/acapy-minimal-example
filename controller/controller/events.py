"""Event Listener."""
import asyncio
from contextlib import asynccontextmanager, suppress
import json
import logging
from typing import Any, AsyncIterator, Mapping

from aiohttp import ClientSession, WSMsgType
from async_selective_queue import AsyncSelectiveQueue as Queue
from attr import dataclass

LOGGER = logging.getLogger(__name__)


@dataclass
class Event:
    """Event data class."""

    topic: str
    payload: Mapping[str, Any]


@asynccontextmanager
async def EventQueue(name: str, url: str) -> AsyncIterator[Queue[Event]]:
    """Create event queue."""
    event_queue: Queue[Event] = Queue()
    ws_task = asyncio.get_event_loop().create_task(ws(name, url, event_queue))

    yield event_queue

    ws_task.cancel()
    with suppress(asyncio.CancelledError):
        await ws_task
    ws_task = None


async def ws(name: str, url: str, queue: Queue[Event]):
    """WS Task."""
    async with ClientSession(url) as session:
        async with session.ws_connect("/ws", timeout=30.0) as ws:
            try:
                async for msg in ws:
                    if msg.type == WSMsgType.TEXT:
                        data = msg.json()
                        if data.get("topic") != "ping":
                            try:
                                event = Event(**data)
                                LOGGER.debug("%s: %s", name, event)
                                await queue.put(event)
                            except Exception:
                                LOGGER.warning(
                                    "Unable to parse event: %s",
                                    json.dumps(data, indent=2),
                                )
                        elif data.get("topic") == "ping":
                            LOGGER.debug("%s: WS Ping received", name)
                    if msg.type == WSMsgType.ERROR:
                        # TODO Can we continue after ERROR?
                        break
            finally:
                if not ws.closed:
                    await ws.close()
