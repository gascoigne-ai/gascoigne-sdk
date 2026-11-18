"""Process adapter: finds the gascoigne CLI and asks it to start its background server."""

from __future__ import annotations

import os
import shutil
import subprocess


def find_cli() -> str | None:
    """Path of the CLI: $GASCOIGNE_BIN, else the first `gascoigne` on PATH."""
    return os.environ.get("GASCOIGNE_BIN") or shutil.which("gascoigne")


def start_server(exe: str) -> None:
    """Run `gascoigne server start`. Raises OSError or SubprocessError on failure."""
    subprocess.run([exe, "server", "start"], capture_output=True, timeout=10, check=False)
