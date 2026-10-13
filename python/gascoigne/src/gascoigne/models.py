"""Wire types of the `/sdk/v1` protocol (see spec/protocol.md)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


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
