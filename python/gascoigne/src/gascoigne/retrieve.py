"""Picking the part of an original that a model asks for."""

from __future__ import annotations

import re

MAX_LINES = 200


def select(text: str, grep: str = "", lines: str = "") -> str:
    """Numbered lines of ``text``, narrowed by a regex (``grep``) or a range (``lines``, "10-20").

    The result is capped at 200 lines so that asking for the original cannot undo the saving.
    """
    numbered = list(enumerate(text.splitlines(), 1))
    if lines:
        first, _, last = lines.partition("-")
        start, end = int(first or 1), int(last or first or len(numbered))
        numbered = [(n, row) for n, row in numbered if start <= n <= end]
    if grep:
        pattern = re.compile(grep)
        numbered = [(n, row) for n, row in numbered if pattern.search(row)]
    shown = [f"{n}: {row}" for n, row in numbered[:MAX_LINES]]
    if len(numbered) > MAX_LINES:
        shown.append(f"... {len(numbered) - MAX_LINES} more lines; narrow with grep or lines")
    return "\n".join(shown)
