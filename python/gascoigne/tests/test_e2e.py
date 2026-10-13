"""Against a real gascoigne binary: GASCOIGNE_BIN=path uv run pytest -m e2e."""

import json
import os
import shutil
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import httpx
import pytest
from gascoigne.runtime import Runtime

pytestmark = pytest.mark.e2e

LOG = (
    "\n".join(
        f"2026-10-13T12:00:{i % 60:02d}Z INFO worker-{i % 7} handled request id={i} took={i % 90}ms"
        for i in range(400)
    )
    + "\n2026-10-13T12:09:01Z ERROR db timeout after 30s\n"
)


@pytest.fixture
def server(tmp_path, monkeypatch):
    exe = os.environ.get("GASCOIGNE_BIN") or shutil.which("gascoigne")
    if not exe:
        pytest.skip("no gascoigne binary")
    monkeypatch.setenv("GASCOIGNE_BIN", exe)
    monkeypatch.setenv("GASCOIGNE_SERVER_ADDR", "127.0.0.1:7899")
    monkeypatch.setenv("GASCOIGNE_LEDGER", str(tmp_path / "l.db"))
    yield
    os.system(f"GASCOIGNE_SERVER_ADDR=127.0.0.1:7899 {exe} server stop >/dev/null 2>&1")


def test_optimize_and_raw(server):
    rt = Runtime(agent="e2e")
    res = rt.optimize_result(LOG, tool="logs")
    assert res.raw_id and len(res.text) < len(LOG) and "db timeout" in res.text
    assert rt.raw(res.raw_id) == LOG


class _Upstream(BaseHTTPRequestHandler):
    """Stands in for the LLM API: remembers the last request body."""

    received: list[dict[str, Any]] = []

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Upstream.received.append(body)
        reply = json.dumps(
            {
                "id": "x",
                "object": "chat.completion",
                "model": "m",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "ok"},
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(reply)))
        self.end_headers()
        self.wfile.write(reply)

    def log_message(self, *_: object) -> None:
        pass


def test_proxy_shortens_tool_results_without_wrapping(tmp_path, monkeypatch):
    upstream = HTTPServer(("127.0.0.1", 0), _Upstream)
    threading.Thread(target=upstream.serve_forever, daemon=True).start()
    config = tmp_path / "config.yaml"
    config.write_text(
        f"receivers:\n  httpproxy:\n    openai: http://127.0.0.1:{upstream.server_port}\n"
    )
    exe = os.environ.get("GASCOIGNE_BIN") or shutil.which("gascoigne")
    if not exe:
        pytest.skip("no gascoigne binary")
    monkeypatch.setenv("GASCOIGNE_BIN", exe)
    monkeypatch.setenv("GASCOIGNE_CONFIG", str(config))
    monkeypatch.setenv("GASCOIGNE_SERVER_ADDR", "127.0.0.1:7898")
    monkeypatch.setenv("GASCOIGNE_LEDGER", str(tmp_path / "l.db"))
    try:
        base = Runtime().proxy_base_url("openai")
        assert base
        call = {
            "id": "call_1",
            "type": "function",
            "function": {"name": "search_logs", "arguments": "{}"},
        }
        messages = [
            {"role": "user", "content": "what went wrong?"},
            {"role": "assistant", "content": None, "tool_calls": [call]},
            {"role": "tool", "tool_call_id": "call_1", "content": LOG},
        ]
        r = httpx.post(
            f"{base}/chat/completions", json={"model": "m", "messages": messages}, timeout=10
        )
        r.raise_for_status()
        seen = _Upstream.received[-1]["messages"][-1]["content"]
        assert len(seen) < len(LOG) // 4 and "db timeout" in seen
    finally:
        os.system(f"GASCOIGNE_SERVER_ADDR=127.0.0.1:7898 {exe} server stop >/dev/null 2>&1")
        upstream.shutdown()
