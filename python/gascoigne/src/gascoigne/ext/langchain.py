"""LangChain / LangGraph: optimize what tools return before the model reads it."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from gascoigne.runtime import Runtime, default


def optimize_tools(tools: Iterable[Any], runtime: Runtime | None = None) -> list[Any]:
    """Wrap ``func`` / ``coroutine`` of every StructuredTool in place; other tools pass through."""
    rt = runtime or default()
    out = list(tools)
    for t in out:
        for attr in ("func", "coroutine"):
            fn = getattr(t, attr, None)
            if callable(fn):
                setattr(t, attr, rt.wrap_tool(fn, name=getattr(t, "name", "")))
    return out
