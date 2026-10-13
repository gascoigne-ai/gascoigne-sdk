"""Against a real gascoigne binary: GASCOIGNE_BIN=path uv run pytest -m e2e."""

import os
import shutil

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
