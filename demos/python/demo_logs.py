"""The noisy tool shared by the demos. Imports nothing, so an MCP server can use it."""

import random


def search_logs() -> str:
    """Return the recent service logs."""
    # Request ids differ per call, as in real logs; the proxy caches identical results.
    first_id = random.randrange(900_000)
    lines = [
        f"2026-10-13T12:{i // 60:02d}:{i % 60:02d}Z INFO worker-{i % 7} handled request "
        f"id={first_id + i} status=200 took={i % 90}ms"
        for i in range(400)
    ]
    lines.insert(250, "2026-10-13T12:04:10Z ERROR db connection timeout after 30s (pool exhausted)")
    return "\n".join(lines)
