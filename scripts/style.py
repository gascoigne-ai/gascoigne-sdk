#!/usr/bin/env python3
"""Checks what linters do not: 100 columns, no trailing comments, ASCII-only source.

See .harness/code-style.md. Usage: scripts/style.py
"""

import re
import subprocess
import sys
from pathlib import Path

MAX_COLS = 100
SOURCE = {".py", ".ts", ".go", ".rs", ".java", ".cs"}
# every other language here uses "//"
LINE_COMMENT = {".py": "#"}
STRING = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`[^`]*`')


def tracked_sources() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split("\n")
    return [Path(p) for p in out if Path(p).suffix in SOURCE and Path(p).exists()]


def trailing_comment(line: str, marker: str) -> bool:
    """True when code precedes a line comment on the same line."""
    code = STRING.sub('""', line)
    head, sep, _ = code.partition(marker)
    return bool(sep) and bool(head.strip()) and not head.rstrip().endswith(marker[0])


def main() -> int:
    problems = []
    for path in tracked_sources():
        marker = LINE_COMMENT.get(path.suffix, "//")
        for no, line in enumerate(path.read_text().splitlines(), 1):
            if len(line.expandtabs(4)) > MAX_COLS:
                problems.append(f"{path}:{no}: longer than {MAX_COLS} columns")
            if not line.isascii():
                problems.append(f"{path}:{no}: non-ASCII character")
            if trailing_comment(line, marker) and "http" not in line:
                problems.append(f"{path}:{no}: trailing comment; put it on the line above")
    print("\n".join(problems) or "style ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
