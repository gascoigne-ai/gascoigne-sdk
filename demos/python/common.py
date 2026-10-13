"""Shared bits of the demos: OpenRouter settings, a noisy tool, and a savings report.

    export OPENROUTER_API_KEY=sk-or-...        # required for real runs
    export OPENROUTER_MODEL=openai/gpt-4o-mini # optional
    uv run --extra langgraph python langgraph_demo.py
    GASCOIGNE_DEMO_DRY=1 uv run --extra langgraph python langgraph_demo.py   # no LLM call

The tool returns a 400-line service log with one error. gascoigne folds the noise before the model
reads it; the answer should still name the error.
"""

import os
import sys

import gascoigne

BASE_URL = "https://openrouter.ai/api/v1"
MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
PROMPT = (
    "Call the search_logs tool once, then tell me in one sentence what went wrong "
    "and for how long."
)


def api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key and not dry():
        sys.exit("OPENROUTER_API_KEY is not set (get one at https://openrouter.ai/keys)")
    return key or "dry-run"


def dry() -> bool:
    return os.environ.get("GASCOIGNE_DEMO_DRY") == "1"


def search_logs() -> str:
    """Return the recent service logs."""
    lines = [
        f"2026-10-13T12:{i // 60:02d}:{i % 60:02d}Z INFO worker-{i % 7} handled request "
        f"id={i} status=200 took={i % 90}ms"
        for i in range(400)
    ]
    lines.insert(
        250, "2026-10-13T12:04:10Z ERROR db connection timeout after 30s (pool exhausted)"
    )
    return "\n".join(lines)


def rt() -> gascoigne.Runtime:
    return gascoigne.init(agent="demo")


def report() -> None:
    s = gascoigne.stats()
    if not s["raw_tokens"]:
        print("\n[gascoigne] bypassed: no savings (is `gascoigne` on PATH?)")
        return
    saved = 100 * (1 - s["out_tokens"] / s["raw_tokens"])
    print(f"\n[gascoigne] tool results: {s['raw_tokens']} -> {s['out_tokens']} tokens (-{saved:.0f}%)")


def dry_call(tool) -> None:
    """Without an LLM: call the registered tool the way the framework would."""
    out = tool()
    print(f"dry run: tool returned {len(out)} chars\n{out[:300]}")
    report()
