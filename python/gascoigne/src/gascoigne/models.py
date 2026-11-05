"""Wire types of the `/sdk/v1` protocol (see spec/protocol.md)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, cast


def _items(data: dict[str, Any], key: str) -> list[Any]:
    """The list under ``key``; a missing or null one is empty."""
    value = data.get(key)
    return cast(list[Any], value) if isinstance(value, list) else []


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
    def from_json(cls, data: dict[str, Any]) -> Result:
        """Parse a response body; raises KeyError/TypeError when it is not one."""
        text = data["text"]
        if not isinstance(text, str):
            raise TypeError("text is not a string")
        return cls(
            text=text,
            raw_id=str(data.get("raw_id", "")),
            raw_tokens=int(data.get("raw_tokens", 0)),
            out_tokens=int(data.get("out_tokens", 0)),
            skipped=str(data.get("skipped", "")),
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

    group: str = ""
    runs: int = 0
    optimized: int = 0
    failed: int = 0
    raw_tokens: int = 0
    out_tokens: int = 0
    saved: int = 0
    # RFC 3339 times of the first and last run, empty when unknown
    first: str = ""
    last: str = ""

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Total:
        return cls(
            group=str(data.get("group", "")),
            runs=int(data.get("runs", 0)),
            optimized=int(data.get("optimized", 0)),
            failed=int(data.get("failed", 0)),
            raw_tokens=int(data.get("raw_tokens", 0)),
            out_tokens=int(data.get("out_tokens", 0)),
            saved=int(data.get("saved", 0)),
            first=str(data.get("first", "")),
            last=str(data.get("last", "")),
        )


@dataclass(frozen=True)
class Run:
    """One recorded optimization (``GET /sdk/v1/recent``)."""

    id: int = 0
    # RFC 3339
    time: str = ""
    session: str = ""
    agent: str = ""
    model: str = ""
    command: str = ""
    route: str = ""
    optimizers: list[str] = field(default_factory=lambda: list[str]())
    raw_tokens: int = 0
    out_tokens: int = 0
    duration_ns: int = 0
    raw_id: str = ""
    outcome: str = ""
    reason: str = ""

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Run:
        return cls(
            id=int(data.get("id", 0)),
            time=str(data.get("time", "")),
            session=str(data.get("session", "")),
            agent=str(data.get("agent", "")),
            model=str(data.get("model", "")),
            command=str(data.get("command", "")),
            route=str(data.get("route", "")),
            optimizers=[str(o) for o in _items(data, "optimizers")],
            raw_tokens=int(data.get("raw_tokens", 0)),
            out_tokens=int(data.get("out_tokens", 0)),
            duration_ns=int(data.get("duration_ns", 0)),
            raw_id=str(data.get("raw_id", "")),
            outcome=str(data.get("outcome", "")),
            reason=str(data.get("reason", "")),
        )
