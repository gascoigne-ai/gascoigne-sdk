"""Discovery of the CLI, the background server, and the never-raise optimize call."""

from __future__ import annotations

import functools
import inspect
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypeVar, cast

import httpx

from gascoigne.models import Costs, OptimizeRequest, Result, Run, Stats, Total
from gascoigne.native import Native, NativeError, Settings
from gascoigne.retrieve import select

log = logging.getLogger("gascoigne")

PROTO = 1
DEFAULT_ADDR = "127.0.0.1:7878"
INSTALL_HINT = "mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne"
BREAKER_FAILURES = 5
BREAKER_PAUSE = 60.0
MODES = ("proxy", "native")

F = TypeVar("F", bound=Callable[..., Any])


class Runtime:
    """Finds the CLI, makes sure its server runs, and optimizes text through it."""

    def __init__(
        self,
        *,
        agent: str = "",
        session: str = "",
        timeout: float = 5.0,
        on_result: Callable[[str, Result], None] | None = None,
        mode: str = "",
        settings: Settings | None = None,
    ) -> None:
        # "native" runs the engine in this process through libgascoigne and raises NativeError
        # here when the library cannot be found or loaded; "proxy" talks to the gascoigne server.
        # Empty means $GASCOIGNE_MODE, else proxy.
        self.mode = mode or os.environ.get("GASCOIGNE_MODE", "") or "proxy"
        self.settings = settings or Settings()
        self._native: Native | None = Native(self.settings) if self.mode == "native" else None
        self.agent = agent
        self.session = session
        self.timeout = timeout
        # called with (original, result) after each optimized call
        self.on_result = on_result
        self._lock = threading.Lock()
        # None until probed
        self._available: bool | None = None
        self._failures = 0
        self._paused_until = 0.0
        self._warned = False
        self._client: httpx.Client | None = None
        self._stats = Stats()

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
            if self._available is None:
                if self._native is not None:
                    self._available = True
                else:
                    self._available = self._healthy() or self._start_server()
            return self._available and time.monotonic() >= self._paused_until

    def close(self) -> None:
        """Release the embedded engine, if any."""
        if self._native:
            self._native.close()
            self._native = None
            self._available = False

    def _failed(self, why: object) -> None:
        log.debug("gascoigne optimize failed: %s", why)
        with self._lock:
            self._failures += 1
            if self._failures >= BREAKER_FAILURES:
                self._failures = 0
                self._paused_until = time.monotonic() + BREAKER_PAUSE
                log.debug("gascoigne breaker open for %ss", BREAKER_PAUSE)

    def optimize_result(
        self,
        text: str,
        *,
        tool: str = "",
        cmd: str = "",
        url: str = "",
        query: str = "",
        model: str = "",
    ) -> Result:
        """Optimize ``text``. ``tool``..``model`` say where it came from and guide the optimizer."""
        if not text or not self.ready():
            return Result(text)
        request = OptimizeRequest(
            text, self.agent, self.session, tool=tool, cmd=cmd, url=url, query=query, model=model
        )
        try:
            if self._native:
                out = self._native.optimize(request)
            else:
                response = self._http().post("/sdk/v1/optimize", json=request.to_json())
                response.raise_for_status()
                out = Result.from_json(response.json())
        except (httpx.HTTPError, NativeError, ValueError, KeyError, TypeError) as e:
            self._failed(e)
            return Result(text)
        with self._lock:
            self._failures = 0
            self._stats = Stats(
                self._stats.raw_tokens + out.raw_tokens,
                self._stats.out_tokens + (out.out_tokens or out.raw_tokens),
            )
        self._notify(text, out)
        return out

    def _notify(self, original: str, result: Result) -> None:
        if not self.on_result:
            return
        try:
            self.on_result(original, result)
        # an observer must never break the host app
        except Exception as e:
            log.debug("on_result failed: %s", e)

    def stats(self) -> Stats:
        """Tokens (estimated) before and after, summed over this runtime's calls."""
        return self._stats

    def optimize(self, text: str, **attrs: str) -> str:
        """The text the model should read; ``attrs`` as in `optimize_result`."""
        return self.optimize_result(text, **attrs).text

    def raw(self, raw_id: str) -> str:
        """The original behind an optimized result; empty when unavailable."""
        if not self.ready():
            return ""
        try:
            if self._native:
                return self._native.raw(raw_id)
            r = self._http().get(f"/sdk/v1/raw/{raw_id}")
            r.raise_for_status()
            return r.text
        except (httpx.HTTPError, NativeError) as e:
            self._failed(e)
            return ""

    def totals(
        self,
        *,
        by: str = "",
        session: str = "",
        agent: str = "",
        model: str = "",
        since: datetime | None = None,
    ) -> list[Total]:
        """The recorded runs summed per group: ``by`` is route, session, family, optimizer,
        command, outcome, agent, model, day, week or month (default route). Empty filters match
        everything. Reads never raise and never trip the optimize breaker: on any failure
        (bypass, server down, a bad query) the answer is an empty list.
        """
        query = _query(by=by, session=session, agent=agent, model=model, since=_rfc3339(since))
        try:
            if self._native:
                return self._native.totals(query)
            return [Total.from_json(d) for d in self._read("/sdk/v1/stats", query)]
        except (httpx.HTTPError, NativeError, ValueError, KeyError, TypeError) as e:
            log.debug("gascoigne totals failed: %s", e)
            return []

    def runs(
        self,
        *,
        session: str = "",
        agent: str = "",
        model: str = "",
        since: datetime | None = None,
        before: int = 0,
        limit: int = 0,
    ) -> list[Run]:
        """The recorded runs, newest first. ``before`` is a run id (only older runs come back,
        to page); ``limit`` defaults to 50, at most 1000. Never raises: empty on failure.
        """
        query = _query(session=session, agent=agent, model=model, since=_rfc3339(since))
        if before > 0:
            query["before"] = str(before)
        if limit > 0:
            query["limit"] = str(limit)
        try:
            if self._native:
                native_query: dict[str, str | int] = {**query}
                for key in ("before", "limit"):
                    if key in query:
                        native_query[key] = int(query[key])
                return self._native.runs(native_query)
            return [Run.from_json(d) for d in self._read("/sdk/v1/recent", query)]
        except (httpx.HTTPError, NativeError, ValueError, KeyError, TypeError) as e:
            log.debug("gascoigne runs failed: %s", e)
            return []

    def costs(
        self,
        *,
        session: str = "",
        agent: str = "",
        model: str = "",
        since: datetime | None = None,
    ) -> Costs:
        """What the tokens saved are worth: an estimate, not a bill. ``billing`` says "api" or
        "subscription" (no dollars). Never raises: an empty `Costs` on failure.
        """
        query = _query(session=session, agent=agent, model=model, since=_rfc3339(since))
        try:
            if self._native:
                return self._native.costs(query)
            return Costs.from_json(self._read("/sdk/v1/costs", query))
        except (httpx.HTTPError, NativeError, ValueError, KeyError, TypeError) as e:
            log.debug("gascoigne costs failed: %s", e)
            return Costs()

    def _read(self, path: str, query: dict[str, str]) -> Any:
        """GET a ledger route; raises on any failure, for the callers above to absorb."""
        if not self.ready():
            raise ValueError("gascoigne is not available")
        response = self._http().get(path, params=query)
        response.raise_for_status()
        return response.json()

    def retrieve(self, raw_id: str, grep: str = "", lines: str = "") -> str:
        """Part of an original, for a model that needs what was folded.

        ``grep`` is a regex matched per line, ``lines`` a range such as "10-40". Both are optional.
        """
        original = self.raw(raw_id)
        if not original:
            return f"No original stored for {raw_id}."
        try:
            return select(original, grep, lines)
        except (ValueError, re.error) as e:
            return f"Bad selection: {e}"

    def proxy_base_url(self, api: str = "openai") -> str | None:
        """Base URL that routes an LLM client through the gascoigne proxy, or None in bypass.

        ``api`` is "openai" (``/v1``), "anthropic" (no suffix) or "gemini" (no suffix).
        """
        # The embedded engine has no listening proxy.
        if not self.ready() or self._native:
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

            return cast(F, awrapper)

        @functools.wraps(fn)
        def wrapper(*a: Any, **kw: Any) -> Any:
            out = fn(*a, **kw)
            return self.optimize(out, tool=tool) if isinstance(out, str) else out

        return cast(F, wrapper)


def _query(**fields: str) -> dict[str, str]:
    """The non-empty fields."""
    return {k: v for k, v in fields.items() if v}


def _rfc3339(when: datetime | None) -> str:
    if when is None:
        return ""
    if when.tzinfo is None:
        when = when.astimezone()
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_default: Runtime | None = None


def default() -> Runtime:
    """The process-wide runtime, created on first use."""
    global _default
    if _default is None:
        _default = Runtime()
    return _default


def init(
    *,
    agent: str = "",
    session: str = "",
    timeout: float = 5.0,
    on_result: Callable[[str, Result], None] | None = None,
    mode: str = "",
    settings: Settings | None = None,
) -> Runtime:
    """Configure the process-wide runtime and return it.

    ``mode`` is "proxy" or "native" (see spec/native.md); ``settings`` is merged by the library.
    Native mode raises `NativeError` here when no library is found.
    """
    global _default
    _default = Runtime(
        agent=agent,
        session=session,
        timeout=timeout,
        on_result=on_result,
        mode=mode,
        settings=settings,
    )
    return _default


def optimize(text: str, **attrs: str) -> str:
    return default().optimize(text, **attrs)


def raw(raw_id: str) -> str:
    return default().raw(raw_id)


def proxy_base_url(api: str = "openai") -> str | None:
    return default().proxy_base_url(api)


def wrap_tool(fn: F, *, name: str = "") -> F:
    return default().wrap_tool(fn, name=name)


def stats() -> Stats:
    return default().stats()


def totals(**query: Any) -> list[Total]:
    return default().totals(**query)


def runs(**query: Any) -> list[Run]:
    return default().runs(**query)


def costs(**query: Any) -> Costs:
    return default().costs(**query)


def retrieve_original(raw_id: str, grep: str = "", lines: str = "") -> str:
    """Get lines of the original output behind a "gascoigne raw <id>" hint.

    Use ``grep`` (a regex) or ``lines`` (for example "10-40") to ask for just the part you need.
    """
    return default().retrieve(raw_id, grep, lines)
