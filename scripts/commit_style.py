#!/usr/bin/env python3
"""Checks commit subjects against .harness/commit-style.md.

Usage: scripts/commit_style.py [range]   (default: origin/master..HEAD)
"""

import re
import subprocess
import sys

TYPES = "feat|fix|docs|test|refactor|build|ci|release"
# The description starts lower case unless it opens with a name or identifier (Spring, UseFoo).
SUBJECT = re.compile(rf"^({TYPES})(\([a-z0-9][a-z0-9-]*\))?: [A-Za-z0-9`$@/.\-].*[^.]$")
MAX_SUBJECT = 72


def subjects(revision_range: str) -> list[str]:
    out = subprocess.run(
        ["git", "log", "--format=%s", revision_range], capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()


def main() -> int:
    revision_range = sys.argv[1] if len(sys.argv) > 1 else "origin/master..HEAD"
    problems = []
    for subject in subjects(revision_range):
        if not SUBJECT.match(subject):
            problems.append(f"not '<type>(<scope>): <subject>': {subject}")
        elif len(subject) > MAX_SUBJECT:
            problems.append(f"longer than {MAX_SUBJECT} characters: {subject}")
    print("\n".join(problems) or "commit subjects ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
