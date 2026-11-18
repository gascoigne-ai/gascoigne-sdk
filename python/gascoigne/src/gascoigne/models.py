"""Wire types of the `/sdk/v1` protocol (see spec/protocol.md).

Every response is decoded once, here, into a typed model; nothing past this module sees an untyped
map. A required field that is missing or has the wrong type raises KeyError or TypeError, an
optional one (marked ``?`` in the protocol) falls back to its empty value.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, cast


class _Open(StrEnum):
    """A StrEnum that keeps values it does not know: the server's set can grow."""

    @classmethod
    def _missing_(cls, value: object) -> _Open | None:
        if not isinstance(value, str):
            return None
        member = str.__new__(cls, value)
        member._name_ = value
        member._value_ = value
        return member


class Outcome(_Open):
    """What happened to a recorded run."""

    OPTIMIZED = "optimized"
    UNCHANGED = "unchanged"
    BYPASSED = "bypassed"
    REREQUESTED = "rerequested"
    ERROR = "error"


class Route(_Open):
    """The optimizer chain a run took. Routes come from the server's config, so others occur."""

    DEFAULT = "default"
    FOLD = "fold"
    SKILL = "skill"
    PROMPT = "prompt"
    TOOLS = "tools"
    IMAGE = "image"


def _obj(data: object) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError("body is not an object")
    return cast(dict[str, Any], data)


def _str(data: dict[str, Any], key: str, *, required: bool = False) -> str:
    value = data[key] if required else data.get(key, "")
    if not isinstance(value, str):
        raise TypeError(f"{key} is not a string")
    return value


def _int(data: dict[str, Any], key: str, *, required: bool = False) -> int:
    value = data[key] if required else data.get(key, 0)
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{key} is not an integer")
    return value


def _strs(data: dict[str, Any], key: str) -> list[str]:
    """The strings under ``key``; a missing or null list is empty."""
    value = data.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in cast(list[Any], value)):
        raise TypeError(f"{key} is not a list of strings")
    return list(cast(list[str], value))


def _list(parse: Any, data: object) -> list[Any]:
    if not isinstance(data, list):
        raise TypeError("body is not a list")
    return [parse(d) for d in cast(list[Any], data)]


@dataclass(frozen=True)
class Health:
    """`GET /sdk/v1/health`."""

    version: str
    proto: int
    proxy: bool

    @classmethod
    def from_json(cls, data: object) -> Health:
        body = _obj(data)
        proxy = body["proxy"]
        if not isinstance(proxy, bool):
            raise TypeError("proxy is not a boolean")
        return cls(_str(body, "version", required=True), _int(body, "proto", required=True), proxy)


@dataclass(frozen=True)
class OptimizeRequest:
    """Body of `POST /sdk/v1/optimize`. Empty fields are not sent."""

    text: str
    agent: str = ""
    session: str = ""
    tool: str = ""
    cmd: str = ""
    url: str = ""
    query: str = ""
    model: str = ""

    def to_json(self) -> dict[str, str]:
        return {k: v for k, v in asdict(self).items() if v}


@dataclass(frozen=True)
class Result:
    """One optimize call: ``text`` is what the model should read."""

    text: str
    raw_id: str = ""
    raw_tokens: int = 0
    out_tokens: int = 0
    skipped: str = ""

    @classmethod
    def from_json(cls, data: object) -> Result:
        """Parse a response body; raises KeyError/TypeError when it is not one."""
        body = _obj(data)
        return cls(
            text=_str(body, "text", required=True),
            raw_id=_str(body, "raw_id"),
            raw_tokens=_int(body, "raw_tokens", required=True),
            out_tokens=_int(body, "out_tokens", required=True),
            skipped=_str(body, "skipped"),
        )


@dataclass(frozen=True)
class Stats:
    """Tokens (estimated) before and after, summed over a runtime's calls."""

    raw_tokens: int = 0
    out_tokens: int = 0

    @property
    def saved(self) -> float:
        """Fraction of tokens saved, 0 when nothing was optimized."""
        return 1 - self.out_tokens / self.raw_tokens if self.raw_tokens else 0.0


@dataclass(frozen=True)
class Total:
    """The recorded runs of one group, summed (``GET /sdk/v1/stats``)."""

    group: str
    runs: int
    optimized: int
    failed: int
    raw_tokens: int
    out_tokens: int
    saved: int
    # RFC 3339 times of the first and last run, empty when unknown
    first: str = ""
    last: str = ""

    @classmethod
    def from_json(cls, data: object) -> Total:
        body = _obj(data)
        return cls(
            group=_str(body, "group", required=True),
            runs=_int(body, "runs", required=True),
            optimized=_int(body, "optimized", required=True),
            failed=_int(body, "failed", required=True),
            raw_tokens=_int(body, "raw_tokens", required=True),
            out_tokens=_int(body, "out_tokens", required=True),
            saved=_int(body, "saved", required=True),
            first=_str(body, "first"),
            last=_str(body, "last"),
        )

    @classmethod
    def parse_list(cls, data: object) -> list[Total]:
        """The body of `GET /sdk/v1/stats`."""
        return cast(list[Total], _list(cls.from_json, data))


@dataclass(frozen=True)
class Run:
    """One recorded optimization (``GET /sdk/v1/recent``)."""

    id: int
    # RFC 3339
    time: str
    raw_tokens: int
    out_tokens: int
    duration_ns: int
    outcome: Outcome
    session: str = ""
    agent: str = ""
    model: str = ""
    command: str = ""
    # None when the server did not record one
    route: Route | None = None
    optimizers: list[str] = field(default_factory=lambda: list[str]())
    raw_id: str = ""
    reason: str = ""

    @classmethod
    def from_json(cls, data: object) -> Run:
        body = _obj(data)
        route = _str(body, "route")
        return cls(
            id=_int(body, "id", required=True),
            time=_str(body, "time", required=True),
            raw_tokens=_int(body, "raw_tokens", required=True),
            out_tokens=_int(body, "out_tokens", required=True),
            duration_ns=_int(body, "duration_ns", required=True),
            outcome=Outcome(_str(body, "outcome", required=True)),
            session=_str(body, "session"),
            agent=_str(body, "agent"),
            model=_str(body, "model"),
            command=_str(body, "command"),
            route=Route(route) if route else None,
            optimizers=_strs(body, "optimizers"),
            raw_id=_str(body, "raw_id"),
            reason=_str(body, "reason"),
        )

    @classmethod
    def parse_list(cls, data: object) -> list[Run]:
        """The body of `GET /sdk/v1/recent`."""
        return cast(list[Run], _list(cls.from_json, data))
