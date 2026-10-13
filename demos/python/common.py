"""Shared bits of the demos: OpenRouter settings, a noisy tool, and a pretty before/after report.

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
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

BASE_URL = "https://openrouter.ai/api/v1"
MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
PROMPT = (
    "Call the search_logs tool once, then tell me in one sentence what went wrong "
    "and for how long."
)
console = Console()
_seen: list[tuple[str, gascoigne.Result]] = []


def api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key and not dry():
        console.print("[red]OPENROUTER_API_KEY is not set[/] (https://openrouter.ai/keys)")
        sys.exit(1)
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


def rt(framework: str = "demo") -> gascoigne.Runtime:
    console.print(
        Panel.fit(
            Text.assemble(("🌘 gascoigne", "bold"), "  ·  agents read less, nothing gets lost\n")
            + Text(f"{framework} → OpenRouter ({MODEL})", style="dim"),
            border_style="cyan",
        )
    )
    return gascoigne.init(agent=framework, on_result=lambda before, res: _seen.append((before, res)))


def _preview(text: str, n: int = 9) -> Text:
    lines = text.splitlines()
    shown = lines[:n] + ([f"… {len(lines) - n} more lines"] if len(lines) > n else [])
    return Text("\n".join(s[:70] for s in shown), no_wrap=True, overflow="ellipsis")


def report(answer: str | None = None) -> None:
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
        Columns(
            [
                Panel(_preview(before), title=f"🐘 tool result · {res.raw_tokens} tokens", border_style="red", width=48),
                Panel(_preview(res.text), title=f"🌘 model reads · {res.out_tokens} tokens", border_style="green", width=48),
            ]
        )
    )
    s = gascoigne.stats()
    raw, out = s["raw_tokens"], s["out_tokens"]
    saved = 1 - out / raw if raw else 0
    bar = ProgressBar(total=raw, completed=out, width=40, complete_style="green", style="red")
    t = Table.grid(padding=(0, 2))
    t.add_row("saved", Text(f"{saved:.0%}", style="bold green"), bar)
    t.add_row("tokens", f"{raw:,} → {out:,}", Text(f"original kept: gascoigne raw {res.raw_id}", style="dim"))
    console.print(Panel(Group(t), title="📉 savings", border_style="cyan"))


def dry_call(tool) -> None:
    """Without an LLM: call the registered tool the way the framework would."""
    console.print("[dim]dry run: no LLM call, only the tool[/]")
    tool()
    report()
