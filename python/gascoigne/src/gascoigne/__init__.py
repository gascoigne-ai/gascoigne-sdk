"""Embed gascoigne token optimization in agent frameworks.

Every call is safe: when the gascoigne CLI is missing or the server misbehaves, inputs come back
unchanged and nothing is raised.
"""

from gascoigne.runtime import (
    Result,
    Runtime,
    default,
    init,
    optimize,
    proxy_base_url,
    raw,
    stats,
    wrap_tool,
)

__all__ = [
    "Result",
    "Runtime",
    "default",
    "init",
    "optimize",
    "proxy_base_url",
    "raw",
    "stats",
    "wrap_tool",
]
