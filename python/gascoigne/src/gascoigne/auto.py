"""Opt-in, reversible decoration of the tool-call chokepoints of installed libraries.

Nothing here runs unless the application calls :func:`auto`. Each patch is applied only when the
library is installed, wraps the original method, and is removed again by :meth:`AutoHandle.undo`.
"""

from __future__ import annotations

import functools
import importlib
import importlib.util
import logging
from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from typing import Any, cast

from gascoigne.runtime import Runtime, default

log = logging.getLogger("gascoigne")

# Text gascoigne appends to what it shortened; such text is never optimized twice.
HINT = "full: gascoigne raw"
DEFAULT_MIN_CHARS = 800

Shorten = Callable[[str, str], str]


@dataclass
class AutoHandle:
    """What :func:`auto` patched, and the way back."""

    patched: list[str] = field(default_factory=lambda: list[str]())
    _undo: list[Callable[[], None]] = field(default_factory=lambda: list[Callable[[], None]]())

    def on_undo(self, restore: Callable[[], None]) -> None:
        """Register how to restore one patch."""
        self._undo.append(restore)

    def undo(self) -> None:
        """Restore every patched method. Safe to call twice."""
        while self._undo:
            self._undo.pop()()
        self.patched.clear()


_active: AutoHandle | None = None


def auto(
    *,
    skip: Collection[str] = (),
    only: Collection[str] | None = None,
    min_chars: int = DEFAULT_MIN_CHARS,
    runtime: Runtime | None = None,
) -> AutoHandle:
    """Optimize the text results of tools and MCP calls made through installed libraries.

    Covers the MCP client (``mcp.ClientSession.call_tool``) and LangChain / LangGraph tools
    (``BaseTool.invoke`` and ``ainvoke``). ``skip`` names tools never touched, ``only`` limits the
    decoration to the named tools, and results shorter than ``min_chars`` are not sent at all.
    Calling it again replaces the previous settings.
    """
    global _active
    if _active:
        _active.undo()
    rt = runtime or default()

    def shorten(text: str, tool: str) -> str:
        if tool in skip or (only is not None and tool not in only):
            return text
        if len(text) < min_chars or HINT in text:
            return text
        return rt.optimize(text, tool=tool)

    handle = AutoHandle()
    for name, patch in (("mcp", _patch_mcp), ("langchain", _patch_langchain)):
        if importlib.util.find_spec(_MODULES[name]) is None:
            continue
        try:
            patch(shorten, handle)
            handle.patched.append(name)
        # A changed library must not break the application.
        except Exception as e:
            log.warning("gascoigne.auto: could not patch %s (%s); skipped", name, e)
    _active = handle
    return handle


_MODULES = {"mcp": "mcp", "langchain": "langchain_core"}


def _replace(owner: Any, attr: str, make: Callable[[Any], Any], handle: AutoHandle) -> None:
    original = getattr(owner, attr)
    setattr(owner, attr, make(original))
    handle.on_undo(lambda: setattr(owner, attr, original))


def _patch_mcp(shorten: Shorten, handle: AutoHandle) -> None:
    session = importlib.import_module("mcp").ClientSession

    def make(original: Any) -> Any:
        @functools.wraps(original)
        async def call_tool(self: Any, name: str, *args: Any, **kwargs: Any) -> Any:
            return _shorten_mcp(await original(self, name, *args, **kwargs), name, shorten)

        return call_tool

    _replace(session, "call_tool", make, handle)


def _shorten_mcp(result: Any, tool: str, shorten: Shorten) -> Any:
    """Shorten the text parts of a tool result. Errors are never touched.

    Servers often send the same text twice, as a content part and as ``{"result": text}`` in
    ``structuredContent``. Both are shortened together; richer structured data stays as it is, for
    code that reads it.
    """
    content = getattr(result, "content", None)
    is_error, structured_field = _mcp_fields(result)
    if not isinstance(content, list) or getattr(result, is_error, False):
        return result
    structured = getattr(result, structured_field, None)
    parts: list[Any] = []
    for part in cast("list[Any]", content):
        text = getattr(part, "text", None)
        if getattr(part, "type", None) == "text" and isinstance(text, str):
            short = shorten(text, tool)
            if structured == {"result": text}:
                structured = {"result": short}
            part = part.model_copy(update={"text": short})
        parts.append(part)
    return result.model_copy(update={"content": parts, structured_field: structured})


def _mcp_fields(result: Any) -> tuple[str, str]:
    """Names of the error flag and structured content: camelCase in mcp 1.x, snake_case in 2.x."""
    if hasattr(result, "is_error"):
        return "is_error", "structured_content"
    return "isError", "structuredContent"


def _patch_langchain(shorten: Shorten, handle: AutoHandle) -> None:
    base = importlib.import_module("langchain_core.tools").BaseTool

    def make_sync(original: Any) -> Any:
        @functools.wraps(original)
        def invoke(self: Any, *args: Any, **kwargs: Any) -> Any:
            return _shorten_tool_output(original(self, *args, **kwargs), self.name, shorten)

        return invoke

    def make_async(original: Any) -> Any:
        @functools.wraps(original)
        async def ainvoke(self: Any, *args: Any, **kwargs: Any) -> Any:
            return _shorten_tool_output(await original(self, *args, **kwargs), self.name, shorten)

        return ainvoke

    _replace(base, "invoke", make_sync, handle)
    _replace(base, "ainvoke", make_async, handle)


def _shorten_blocks(blocks: list[Any], tool: str, shorten: Shorten) -> list[Any]:
    """Content blocks as LangChain tools return them: {"type": "text", "text": ...}."""
    shortened: list[Any] = []
    for block in blocks:
        fields = cast("dict[str, Any]", block) if isinstance(block, dict) else {}
        if fields.get("type") == "text" and isinstance(fields.get("text"), str):
            block = {**fields, "text": shorten(fields["text"], tool)}
        shortened.append(block)
    return shortened


def _shorten_tool_output(output: Any, tool: str, shorten: Shorten) -> Any:
    """Shorten a tool's output: a string, text blocks, or a ToolMessage holding either."""
    if isinstance(output, str):
        return shorten(output, tool)
    if isinstance(output, list):
        return _shorten_blocks(cast("list[Any]", output), tool, shorten)
    if hasattr(output, "tool_call_id") and isinstance(
        getattr(output, "content", None), (str, list)
    ):
        content = _shorten_tool_output(output.content, tool, shorten)
        return output.model_copy(update={"content": content})
    return output
