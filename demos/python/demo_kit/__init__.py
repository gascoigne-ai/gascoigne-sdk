"""Everything a demo needs that is NOT about integrating gascoigne: env, OpenRouter, tool, report.

Read the *_demo.py files, not this one.
"""

import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import gascoigne
from dotenv import find_dotenv, load_dotenv
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

load_dotenv(find_dotenv(usecwd=True))

console = Console()
PROMPT = (
    "Call the search_logs tool once, then tell me in one sentence what went wrong and for how long."
)
_seen: list[tuple[str, gascoigne.Result]] = []


def dry() -> bool:
    return os.environ.get("GASCOIGNE_DEMO_DRY") == "1"


def model() -> str:
    return os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")


@dataclass(frozen=True)
class OpenRouterSettings:
    """Connection settings; field names match what OpenAI-compatible clients call them."""

    model: str
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"

    @classmethod
    def from_env(cls) -> "OpenRouterSettings":
        """Read the settings; exit with a hint when the key is missing (except in a dry run)."""
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key and not dry():
            console.print("[red]OPENROUTER_API_KEY is not set[/]: copy .env.example to .env")
            sys.exit(1)
        return cls(model=model(), api_key=api_key or "dry-run")


openrouter = OpenRouterSettings.from_env()


def search_logs() -> str:
    """Return the recent service logs."""
    lines = [
        f"2026-10-13T12:{i // 60:02d}:{i % 60:02d}Z INFO worker-{i % 7} handled request "
        f"id={i} status=200 took={i % 90}ms"
        for i in range(400)
    ]
    lines.insert(250, "2026-10-13T12:04:10Z ERROR db connection timeout after 30s (pool exhausted)")
    return "\n".join(lines)


def _preview(text: str, lines: int = 8) -> Text:
    """The first lines of a text, each cut to 70 characters."""
    rows = text.splitlines()
    shown = rows[:lines]
    if len(rows) > lines:
        shown.append(f"... {len(rows) - lines} more lines")
    return Text("\n".join(row[:70] for row in shown), no_wrap=True, overflow="ellipsis")


def _panel(body: object, title: str, color: str) -> Panel:
    return Panel(body, title=title, title_align="left", border_style=color, box=box.ASCII)


def run(ask: Callable[[], Any], tool: Callable[[], str]) -> None:
    """Run the agent (`ask`), or just the tool in a dry run, then print what gascoigne saved."""
    runtime = gascoigne.default()
    runtime.on_result = lambda before, result: _seen.append((before, result))
    console.print(f"gascoigne demo: {runtime.agent} via OpenRouter ({model()})\n", style="bold")
    answer = None
    if dry():
        console.print("Dry run: no LLM call, only the tool.", style="dim")
        tool()
    else:
        answer = str(ask())
    if answer:
        console.print(_panel(answer.strip(), "Model answer", "green"))
    if not _seen:
        console.print(
            _panel(
                "No optimization happened. Is the gascoigne CLI on PATH?\n"
                "Install: mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne",
                "Bypassed",
                "yellow",
            )
        )
        return
    before, result = _seen[-1]
    console.print(_panel(_preview(before), f"Tool result: {result.raw_tokens:,} tokens", "red"))
    console.print(
        _panel(_preview(result.text), f"Model reads: {result.out_tokens:,} tokens", "green")
    )
    stats = gascoigne.stats()
    summary = Text(f"Saved {stats.saved:.0%}: ", style="bold green")
    summary.append(f"{stats.raw_tokens:,} -> {stats.out_tokens:,} tokens. ")
    summary.append(f"Original: gascoigne raw {result.raw_id}", style="dim")
    console.print(_panel(summary, "Savings", "cyan"))
