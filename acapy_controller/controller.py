"""ACA-Py Controller."""

import asyncio
from contextlib import AsyncExitStack
from dataclasses import asdict, dataclass, field, fields, is_dataclass
import dataclasses
import json
import logging
from json import dumps
from types import TracebackType
from typing import (
    Any,
    ClassVar,
    Dict,
    Literal,
    Mapping,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
    overload,
    runtime_checkable,
    get_origin,
)

from aiohttp import ClientResponse, ClientSession
from async_selective_queue import Select

from .events import Event, EventQueue, Queue


LOGGER = logging.getLogger(__name__)
T = TypeVar("T")


@runtime_checkable
class Serde(Protocol):
    """Object supporting serialization and deserialization methods."""

    def serialize(self) -> Mapping[str, Any]:
        """Serialize object."""
        ...

    @classmethod
    def deserialize(cls: Type[T], value: Mapping[str, Any]) -> T:
        """Deserialize value to object."""
        ...


class Dataclass(Protocol):
    """Empty protocol for dataclass type hinting."""

    __dataclass_fields__: ClassVar[dict[str, dataclasses.Field[Any]]]


Serializable = Union[Mapping[str, Any], Serde, Dataclass, None]


def _serialize(value: Serializable):
    """Serialize value."""
    if value is None:
        return None
    if isinstance(value, Serde):
        return value.serialize()
    if isinstance(value, Mapping):
        return value
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Could not serialize value {value}")


@overload
def _deserialize(value: Any) -> Mapping[str, Any]: ...


@overload
def _deserialize(value: Any, as_type: Type[T]) -> T: ...


@overload
def _deserialize(value: Any, as_type: None) -> Mapping[str, Any]: ...


def _deserialize(value: Any, as_type: Optional[Type[T]] = None) -> Union[T, Any]:
    """Deserialize value."""
    if value is None:
        return None
    if as_type is None:
        return value
    if get_origin(as_type) is list:
        args = get_args(as_type)
        return [_deserialize(item, args[0]) for item in value]
    if issubclass(as_type, Serde):
        return as_type.deserialize(value)
    if is_dataclass(as_type):
        return cast(T, as_type(**value))
    if issubclass(as_type, Mapping):
        return cast(T, value)
    raise TypeError(f"Could not deserialize value into type {as_type.__name__}")


MinType = TypeVar("MinType", bound="Minimal")
S = TypeVar("S", bound=Serializable)


@dataclass
class Minimal(Serde, Dataclass, Mapping[str, Any]):
    """Base class for minimized record."""

    _extra: Dict[str, Any] = field(default_factory=dict, kw_only=True)

    @classmethod
    def deserialize(cls: Type[MinType], value: Mapping[str, Any]) -> MinType:
        """Deserialize from a dictionary.

        Subclasses must implement this method to enable handling nested structures.
        """
        filtered = {}
        extra = {}
        field_names = tuple(f.name for f in fields(cls))
        for key, value in value.items():
            if key in field_names:
                filtered[key] = value
            else:
                extra[key] = value

        instance = cls(**filtered, _extra=extra)
        return instance

    def serialize(self) -> Mapping[str, Any]:
        """Serialize to a dictionary."""
        serialized = asdict(self)
        extra = serialized.pop("_extra")
        serialized.update(extra)
        return serialized

    def __getitem__(self, key: str) -> Any:
        """Get an extra field."""
        return self._extra[key]

    def __iter__(self):
        """Iterate over fields."""
        return iter(self.serialize())

    def __len__(self):
        """Return the number of fields."""
        return len(fields(self)) + len(self._extra)

    def into(self, cls: Type[S]) -> S:
        """Convert to another serializable class."""
        flattened = self.serialize()
        return _deserialize(flattened, cls)


def _serialize_param(value: Any):
    return (
        value
        if isinstance(value, (str, int, float)) and not isinstance(value, bool)
        else json.dumps(value)
    )


def params(**kwargs) -> Mapping[str, Any]:
    """Filter out keys with none values from dictionary."""

    return {
        key: _serialize_param(value) for key, value in kwargs.items() if value is not None
    }


def omit_none(mapping: Mapping[str, Any] | None = None, **kwargs):
    """Filter out none values from a mapping."""
    if mapping and kwargs:
        raise ValueError("Either pass a dict or use kwargs but not both")

    if kwargs:
        mapping = kwargs

    if not mapping:
        raise ValueError("Expected mapping or kwargs")

    return {key: value for key, value in mapping.items() if value is not None}


class ControllerError(Exception):
    """Raised on error in controller."""


class ControllerTimeoutError(ControllerError, asyncio.TimeoutError):
    """Raised on timout waiting for event."""


class Controller:
    """ACA-Py Controller."""

    def __init__(
        self,
        base_url: str,
        *,
        label: Optional[str] = None,
        wallet_id: Optional[str] = None,
        subwallet_token: Optional[str] = None,
        wallet_type: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
        event_queue: Optional[Queue[Event]] = None,
    ):
        """Initialize and ACA-Py Controller."""
        self.base_url = base_url
        self.label = label or "ACA-Py"
        self.headers = dict(headers or {})

        if wallet_id and not subwallet_token:
            raise ValueError("subwallet_token required when wallet_id is set")
        self.wallet_id = wallet_id
        self.subwallet_token = subwallet_token
        if subwallet_token:
            self.headers["Authorization"] = f"Bearer {subwallet_token}"
        self._event_queue: Optional[Queue[Event]] = event_queue

        self._stack: Optional[AsyncExitStack] = None

    @property
    def is_subwallet(self) -> bool:
        """Return whether this controller is for a subwallet."""
        return self.subwallet_token is not None

    @property
    def event_queue(self) -> Queue[Event]:
        """Return event queue."""
        if self._event_queue is None:
            raise ControllerError("Controller is not set up")
        return self._event_queue

    async def __aenter__(self):
        """Async context enter."""
        return await self.setup()

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ):
        """Async context exit."""
        await self.shutdown((exc_type, exc_value, traceback))

    async def setup(self) -> "Controller":
        """Set up the controller."""
        self._stack = await AsyncExitStack().__aenter__()
        if not self._event_queue:
            self._event_queue = await self._stack.enter_async_context(EventQueue(self))

        # Get settings
        settings = await self.record("settings")
        self.label = settings["label"]

        # Get wallet type
        config = await self.get("/status/config")
        self.wallet_type = config["config"]["wallet.type"]
        return self

    async def shutdown(self, exc_info: Optional[Tuple] = None):
        """Shutdown the controller."""
        if self._stack:
            await self._stack.__aexit__(*(exc_info or (None, None, None)))

    async def _handle_response(
        self,
        resp: ClientResponse,
        data: Optional[bytes] = None,
        json: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        def _header_filter(headers: Mapping[str, str]):
            return {
                key: value
                for key, value in headers.items()
                if key.lower()
                not in {
                    "host",
                    "accept",
                    "accept-encoding",
                    "user-agent",
                    "content-length",
                    "content-type",
                }
            }

        if data or json:
            LOGGER.info(
                "Request to %s%s %s %s %s",
                self.label,
                _header_filter(resp.request_info.headers) or "",
                resp.method,
                resp.url.path_qs,
                data or dumps(json, sort_keys=True, indent=2),
            )
        else:
            LOGGER.info(
                "Request to %s%s %s %s",
                self.label,
                _header_filter(resp.request_info.headers) or "",
                resp.method,
                resp.url.path_qs,
            )

        if resp.ok and resp.content_type == "application/json":
            body = await resp.json()
            response_out = dumps(body, indent=2, sort_keys=True)
            if response_out.count("\n") > 200:
                response_out = dumps(body, sort_keys=True)
            LOGGER.info("Response: %s", response_out)
            return body

        body = await resp.text()
        if resp.ok:
            raise ControllerError(f"Unexpected content type {resp.content_type}: {body}")
        raise ControllerError(f"Request failed: {resp.url} {body}")

    async def request(
        self,
        method: Literal["GET", "POST", "PUT", "DELETE"],
        url: str,
        *,
        data: Optional[bytes] = None,
        json: Optional[Serializable] = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        response: Optional[Type[T]] = None,
    ) -> Union[T, Mapping[str, Any]]:
        """Make an HTTP request."""
        async with ClientSession(base_url=self.base_url, headers=self.headers) as session:
            headers = dict(headers or {})
            headers.update(self.headers)

            if method == "GET" or method == "DELETE":
                async with session.request(
                    method, url, params=params, headers=headers
                ) as resp:
                    body = await self._handle_response(resp)
                    value = _deserialize(body, response)

            elif method == "POST" or method == "PUT":
                json_ = _serialize(json)
                if not data and json_ is None:
                    json_ = {}

                async with session.request(
                    method, url, data=data, json=json_, params=params
                ) as resp:
                    body = await self._handle_response(resp, data=data, json=json_)
                    value = _deserialize(body, response)
            else:
                raise ValueError(f"Unsupported method {method}")

        return value

    @overload
    async def get(
        self,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Mapping[str, Any]: ...

    @overload
    async def get(
        self,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        response: Type[T],
    ) -> T: ...

    @overload
    async def get(
        self,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        response: None,
    ) -> Mapping[str, Any]: ...

    async def get(
        self,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        response: Optional[Type[T]] = None,
    ) -> Union[T, Mapping[str, Any]]:
        """HTTP Get."""
        return await self.request(
            "GET", url, params=params, headers=headers, response=response
        )

    @overload
    async def delete(
        self,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Mapping[str, Any]: ...

    @overload
    async def delete(
        self,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        response: None,
    ) -> Mapping[str, Any]: ...

    @overload
    async def delete(
        self,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        response: Type[T],
    ) -> T: ...

    async def delete(
        self,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        response: Optional[Type[T]] = None,
    ) -> Union[T, Mapping[str, Any]]:
        """HTTP Delete."""
        return await self.request(
            "DELETE", url, params=params, headers=headers, response=response
        )

    @overload
    async def post(
        self,
        url: str,
        *,
        data: Optional[bytes] = None,
        json: Optional[Serializable] = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Mapping[str, Any]: ...

    @overload
    async def post(
        self,
        url: str,
        *,
        data: Optional[bytes] = None,
        json: Optional[Serializable] = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        response: Type[T],
    ) -> T: ...

    @overload
    async def post(
        self,
        url: str,
        *,
        data: Optional[bytes] = None,
        json: Optional[Serializable] = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        response: None = None,
    ) -> Mapping[str, Any]: ...

    async def post(
        self,
        url: str,
        *,
        data: Optional[bytes] = None,
        json: Optional[Serializable] = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        response: Optional[Type[T]] = None,
    ) -> Union[T, Mapping[str, Any]]:
        """HTTP POST."""
        return await self.request(
            "POST",
            url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            response=response,
        )

    @overload
    async def put(
        self,
        url: str,
        *,
        data: Optional[bytes] = None,
        json: Optional[Serializable] = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Mapping[str, Any]: ...

    @overload
    async def put(
        self,
        url: str,
        *,
        data: Optional[bytes] = None,
        json: Optional[Serializable] = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        response: None,
    ) -> Mapping[str, Any]: ...

    @overload
    async def put(
        self,
        url: str,
        *,
        data: Optional[bytes] = None,
        json: Optional[Serializable] = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        response: Type[T],
    ) -> T: ...

    async def put(
        self,
        url: str,
        *,
        data: Optional[bytes] = None,
        json: Optional[Serializable] = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        response: Optional[Type[T]] = None,
    ) -> Union[T, Mapping[str, Any]]:
        """HTTP Put."""
        return await self.request(
            "PUT",
            url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            response=response,
        )

    @overload
    async def record(
        self,
        topic: str,
        select: Optional[Select[Event]] = None,
    ) -> Mapping[str, Any]: ...

    @overload
    async def record(
        self,
        topic: str,
        select: Optional[Select[Event]] = None,
        *,
        record_type: None,
    ) -> Mapping[str, Any]: ...

    @overload
    async def record(
        self,
        topic: str,
        select: Optional[Select[Event]] = None,
        *,
        record_type: Type[T],
    ) -> T: ...

    async def record(
        self,
        topic: str,
        select: Optional[Select[Event]] = None,
        *,
        record_type: Optional[Type[T]] = None,
    ) -> Union[T, Mapping[str, Any]]:
        """Get a record from an event.

        DEPRECATED: Use `event` instead.
        """
        return await self.event(topic, select=select, event_type=record_type)

    @overload
    async def record_with_values(
        self,
        topic: str,
        *,
        record_type: Type[T],
        **values,
    ) -> T: ...

    @overload
    async def record_with_values(
        self,
        topic: str,
        *,
        record_type: None = None,
        **values,
    ) -> Mapping[str, Any]: ...

    async def record_with_values(
        self,
        topic: str,
        *,
        record_type: Optional[Type[T]] = None,
        timeout: int = 5,
        **values,
    ) -> Union[T, Mapping[str, Any]]:
        """Get a record from an event with values matching those passed in.

        DEPRECATED: Use `event_with_values` instead.
        """
        return await self.event_with_values(
            topic, event_type=record_type, timeout=timeout, **values
        )

    @overload
    async def event(
        self,
        topic: str,
        select: Optional[Select[Event]] = None,
    ) -> Mapping[str, Any]: ...

    @overload
    async def event(
        self,
        topic: str,
        select: Optional[Select[Event]] = None,
        *,
        event_type: None,
    ) -> Mapping[str, Any]: ...

    @overload
    async def event(
        self,
        topic: str,
        select: Optional[Select[Event]] = None,
        *,
        event_type: Type[T],
    ) -> T: ...

    async def event(
        self,
        topic: str,
        select: Optional[Select[Event]] = None,
        *,
        event_type: Optional[Type[T]] = None,
    ) -> Union[T, Mapping[str, Any]]:
        """Await an event matching a given topic and condition."""
        try:
            event = await self.event_queue.get(
                lambda event: event.topic == topic and (select(event) if select else True)
            )
        except asyncio.TimeoutError:
            raise ControllerError(
                f"Event from {self.label} with topic {topic} not received before timeout"
            ) from None
        return _deserialize(event.payload, event_type)

    @overload
    async def event_with_values(
        self,
        topic: str,
        *,
        event_type: Type[T],
        **values,
    ) -> T: ...

    @overload
    async def event_with_values(
        self,
        topic: str,
        *,
        event_type: None = None,
        **values,
    ) -> Mapping[str, Any]: ...

    async def event_with_values(
        self,
        topic: str,
        *,
        event_type: Optional[Type[T]] = None,
        timeout: int = 5,
        **values,
    ) -> Union[T, Mapping[str, Any]]:
        """Await an event matching a given topic and set of values."""
        try:
            event = await self.event_queue.get(
                lambda event: event.topic == topic
                and all(event.payload.get(key) == value for key, value in values.items()),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise ControllerTimeoutError(
                f"Record from {self.label} with topic {topic} and values\n\t{values}\n"
                "not received before timeout"
            ) from None
        return _deserialize(event.payload, event_type)
