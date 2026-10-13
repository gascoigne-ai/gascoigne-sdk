"""Discovery of the CLI, the background server, and the never-raise optimize call."""

from __future__ import annotations

import functools
import inspect
import logging
import os
import shutil
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

import httpx

log = logging.getLogger("gascoigne")

PROTO = 1
DEFAULT_ADDR = "127.0.0.1:7878"
INSTALL_HINT = "mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne"
BREAKER_FAILURES = 5
BREAKER_PAUSE = 60.0

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True)
class Result:
    """One optimize call: ``text`` is what the model should read."""

    text: str
    raw_id: str = ""
    raw_tokens: int = 0
    out_tokens: int = 0
    skipped: str = ""


class Runtime:
    """Finds the CLI, makes sure its server runs, and optimizes text through it."""

    def __init__(self, *, agent: str = "", session: str = "", timeout: float = 5.0) -> None:
        self.agent = agent
        self.session = session
        self.timeout = timeout
        self._lock = threading.Lock()
        self._state: str | None = None  # None: not probed yet, "ready" or "bypass"
        self._failures = 0
        self._paused_until = 0.0
        self._warned = False
        self._client: httpx.Client | None = None
        self._raw_tokens = 0
        self._out_tokens = 0

    @property
    def addr(self) -> str:
        return os.environ.get("GASCOIGNE_SERVER_ADDR") or DEFAULT_ADDR

    @property
    def base_url(self) -> str:
        return f"http://{self.addr}"

    def _disabled(self) -> bool:
        return (
            os.environ.get("GASCOIGNE_SDK") == "off" or os.environ.get("GASCOIGNE_SERVER") == "off"
        )

    def _warn(self, msg: str) -> None:
        if not self._warned:
            self._warned = True
            log.warning("%s", msg)

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)
        return self._client

    def _healthy(self) -> bool:
        try:
            r = httpx.get(f"{self.base_url}/sdk/v1/health", timeout=0.5)
            if r.status_code != 200:
                return False
            proto = r.json().get("proto")
        except (httpx.HTTPError, ValueError):
            return False
        if proto != PROTO:
            self._warn(
                f"gascoigne server speaks proto {proto}, SDK {PROTO}; running without optimization"
            )
            return False
        return True

    def _start_server(self) -> bool:
        exe = os.environ.get("GASCOIGNE_BIN") or shutil.which("gascoigne")
        if not exe:
            self._warn(
                "gascoigne-cli not found on PATH; running without optimization. "
                f"Install: {INSTALL_HINT}"
            )
            return False
        try:
            subprocess.run([exe, "server", "start"], capture_output=True, timeout=10, check=False)
        except (OSError, subprocess.SubprocessError) as e:
            self._warn(f"could not start gascoigne server ({e}); running without optimization")
            return False
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if self._healthy():
                return True
            time.sleep(0.1)
        self._warn("gascoigne server did not come up; running without optimization")
        return False

    def ready(self) -> bool:
        """True when optimize calls will be tried. Probes once, then remembers."""
        if self._disabled():
            return False
        with self._lock:
            if self._state is None:
                ok = self._healthy() or self._start_server()
                self._state = "ready" if ok else "bypass"
            if self._state != "ready":
                return False
            return time.monotonic() >= self._paused_until

    def _failed(self, why: object) -> None:
        log.debug("gascoigne optimize failed: %s", why)
        with self._lock:
            self._failures += 1
            if self._failures >= BREAKER_FAILURES:
                self._failures = 0
                self._paused_until = time.monotonic() + BREAKER_PAUSE
                log.debug("gascoigne breaker open for %ss", BREAKER_PAUSE)

    def optimize_result(self, text: str, **attrs: str) -> Result:
        """Optimize ``text``; ``attrs`` are request fields (tool, cmd, url, query, model)."""
        if not text or not self.ready():
            return Result(text)
        body = {"text": text, "agent": self.agent, "session": self.session}
        body.update({k: v for k, v in attrs.items() if v})
        try:
            r = self._http().post("/sdk/v1/optimize", json={k: v for k, v in body.items() if v})
            r.raise_for_status()
            d = r.json()
            out = Result(
                text=d["text"],
                raw_id=d.get("raw_id", ""),
                raw_tokens=d.get("raw_tokens", 0),
                out_tokens=d.get("out_tokens", 0),
                skipped=d.get("skipped", ""),
            )
        except (httpx.HTTPError, ValueError, KeyError) as e:
            self._failed(e)
            return Result(text)
        with self._lock:
            self._failures = 0
            self._raw_tokens += out.raw_tokens
            self._out_tokens += out.out_tokens or out.raw_tokens
        return out

    def stats(self) -> dict[str, int]:
        """Tokens (estimated) before and after, summed over this runtime's calls."""
        return {"raw_tokens": self._raw_tokens, "out_tokens": self._out_tokens}

    def optimize(self, text: str, **attrs: str) -> str:
        return self.optimize_result(text, **attrs).text

    def raw(self, raw_id: str) -> str:
        """The original behind an optimized result; empty when unavailable."""
        if not self.ready():
            return ""
        try:
            r = self._http().get(f"/sdk/v1/raw/{raw_id}")
            r.raise_for_status()
            return r.text
        except httpx.HTTPError as e:
            self._failed(e)
            return ""

    def proxy_base_url(self, api: str = "openai") -> str | None:
        """Base URL that routes an LLM client through the gascoigne proxy, or None in bypass.

        ``api`` is "openai" (``/v1``), "anthropic" (no suffix) or "gemini" (no suffix).
        """
        if not self.ready():
            return None
        return f"{self.base_url}/v1" if api == "openai" else self.base_url

    def wrap_tool(self, fn: F, *, name: str = "") -> F:
        """Wrap a tool callable so string results are optimized. Sync and async."""
        tool = name or getattr(fn, "__name__", "tool")
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def awrapper(*a: Any, **kw: Any) -> Any:
                out = await fn(*a, **kw)
                return self.optimize(out, tool=tool) if isinstance(out, str) else out

            return awrapper  # type: ignore[return-value]

        @functools.wraps(fn)
        def wrapper(*a: Any, **kw: Any) -> Any:
            out = fn(*a, **kw)
            return self.optimize(out, tool=tool) if isinstance(out, str) else out

        return wrapper  # type: ignore[return-value]


_default = Runtime()


def default() -> Runtime:
    return _default


def init(*, agent: str = "", session: str = "", timeout: float = 5.0) -> Runtime:
    """Configure the process-wide runtime and return it."""
    global _default
    _default = Runtime(agent=agent, session=session, timeout=timeout)
    return _default


def optimize(text: str, **attrs: str) -> str:
    return _default.optimize(text, **attrs)


def raw(raw_id: str) -> str:
    return _default.raw(raw_id)


def proxy_base_url(api: str = "openai") -> str | None:
    return _default.proxy_base_url(api)


def wrap_tool(fn: F, *, name: str = "") -> F:
    return _default.wrap_tool(fn, name=name)


def stats() -> dict[str, int]:
    return _default.stats()
