"""Embed gascoigne token optimization in agent frameworks.

Every call is safe: when the gascoigne CLI is missing or the server misbehaves, inputs come back
unchanged and nothing is raised.
"""

from gascoigne.auto import AutoHandle, auto
from gascoigne.models import OptimizeRequest, Result, Run, Stats, Total
from gascoigne.native import Settings
from gascoigne.runtime import (
    Runtime,
    default,
    init,
    optimize,
    proxy_base_url,
    raw,
    retrieve_original,
    runs,
    stats,
    totals,
    wrap_tool,
)

__all__ = [
    "AutoHandle",
    "auto",
    "retrieve_original",
    "OptimizeRequest",
    "Result",
    "Run",
    "Stats",
    "Runtime",
    "Settings",
    "Total",
    "default",
    "init",
    "optimize",
    "proxy_base_url",
    "raw",
    "runs",
    "stats",
    "totals",
    "wrap_tool",
]
