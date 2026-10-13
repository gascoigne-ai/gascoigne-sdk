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
from rich.console import Console
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

load_dotenv(find_dotenv(usecwd=True))

console = Console()
PROMPT = "Call the search_logs tool once, then tell me in one sentence what went wrong and for how long."
_seen: list[tuple[str, gascoigne.Result]] = []


def dry() -> bool:
    return os.environ.get("GASCOIGNE_DEMO_DRY") == "1"


def model() -> str:
    return os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")


@dataclass(frozen=True)
class OpenRouter:
    """Connection settings; the field names match what OpenAI-compatible clients call them."""

    model: str
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"


def openrouter() -> OpenRouter:
    """Settings from the environment; exits with a hint when the key is missing (except in a dry run)."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key and not dry():
        console.print("[red]OPENROUTER_API_KEY is not set[/]: copy .env.example to .env")
        sys.exit(1)
    return OpenRouter(model=model(), api_key=api_key or "dry-run")


def search_logs() -> str:
    """Return the recent service logs."""
    lines = [
        f"2026-10-13T12:{i // 60:02d}:{i % 60:02d}Z INFO worker-{i % 7} handled request "
        f"id={i} status=200 took={i % 90}ms"
        for i in range(400)
    ]
    lines.insert(250, "2026-10-13T12:04:10Z ERROR db connection timeout after 30s (pool exhausted)")
    return "\n".join(lines)


def _preview(text: str, n: int = 8) -> Text:
    lines = text.splitlines()
    shown = lines[:n] + ([f"… {len(lines) - n} more lines"] if len(lines) > n else [])
    return Text("\n".join(s[:70] for s in shown), no_wrap=True, overflow="ellipsis")


def run(ask: Callable[[], Any], tool: Callable[[], str]) -> None:
    """Run the agent (`ask`), or just the tool in a dry run, then print what gascoigne saved."""
    rt = gascoigne.default()
    rt.on_result = lambda before, res: _seen.append((before, res))
    console.print(
        Panel.fit(
            Text("🌘 gascoigne", style="bold") + Text(f"  {rt.agent} → OpenRouter ({model()})", style="dim"),
            border_style="cyan",
        )
    )
    answer = None
    if dry():
        console.print("[dim]dry run: no LLM call, only the tool[/]")
        tool()
    else:
        answer = str(ask())
    if answer:
        console.print(Panel(answer.strip(), title="🤖 model answer", border_style="green"))
    if not _seen:
        console.print(
            Panel(
                "No optimization happened: is the [bold]gascoigne[/] CLI on PATH?\n"
                "[dim]mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne[/]",
                title="bypassed",
                border_style="yellow",
            )
        )
        return
    before, res = _seen[-1]
    console.print(
        Panel(_preview(before), title=f"🐘 tool result · {res.raw_tokens} tokens", border_style="red")
    )
    console.print(
        Panel(_preview(res.text), title=f"🌘 model reads · {res.out_tokens} tokens", border_style="green")
    )
    stats = gascoigne.stats()
    row = Table.grid(padding=(0, 2))
    row.add_row(
        Text(f"{stats.saved:.0%} saved", style="bold green"),
        ProgressBar(
            total=stats.raw_tokens, completed=stats.out_tokens, width=36, complete_style="green", style="red"
        ),
        Text(
            f"{stats.raw_tokens:,} → {stats.out_tokens:,} tokens · original: gascoigne raw {res.raw_id}",
            style="dim",
        ),
    )
    console.print(Panel(row, title="📉 savings", border_style="cyan"))
