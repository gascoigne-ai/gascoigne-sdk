"""Ledger reads: totals and runs, through the server and through the embedded library."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from gascoigne.models import Run, Total
from gascoigne.native import Settings
from gascoigne.runtime import PROTO, Runtime

LIB = Path(__file__).parents[3] / "native" / "dist" / "libgascoigne.so"
ADDR = "http://127.0.0.1:9"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for var in ("GASCOIGNE_SDK", "GASCOIGNE_SERVER", "GASCOIGNE_BIN"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("GASCOIGNE_SERVER_ADDR", "127.0.0.1:9")


def health(httpx_mock):
    httpx_mock.add_response(url=f"{ADDR}/sdk/v1/health", json={"version": "t", "proto": PROTO})


def test_totals_through_the_server(httpx_mock):
    health(httpx_mock)
    httpx_mock.add_response(
        url=f"{ADDR}/sdk/v1/stats?by=agent&session=s+1&since=2026-11-01T00%3A00%3A00Z",
        json=[
            {
                "group": "sdk",
                "runs": 2,
                "optimized": 2,
                "failed": 0,
                "raw_tokens": 100,
                "out_tokens": 40,
                "saved": 60,
                "first": "2026-11-01T10:00:00Z",
                "last": "2026-11-01T11:00:00Z",
            }
        ],
    )
    since = datetime(2026, 11, 1, tzinfo=timezone.utc)
    totals = Runtime().totals(by="agent", session="s 1", since=since)
    assert totals == [
        Total(
            group="sdk",
            runs=2,
            optimized=2,
            failed=0,
            raw_tokens=100,
            out_tokens=40,
            saved=60,
            first="2026-11-01T10:00:00Z",
            last="2026-11-01T11:00:00Z",
        )
    ]


def test_runs_through_the_server(httpx_mock):
    health(httpx_mock)
    httpx_mock.add_response(
        url=f"{ADDR}/sdk/v1/recent?before=9&limit=5&session=s1",
        json=[
            {
                "id": 7,
                "time": "2026-11-01T10:00:00Z",
                "session": "s1",
                "raw_tokens": 100,
                "out_tokens": 10,
                "raw_id": "abc",
                "outcome": "optimized",
                "optimizers": ["log"],
            }
        ],
    )
    rt = Runtime()
    runs = rt.runs(session="s1", limit=5, before=9)
    assert [type(r) for r in runs] == [Run]
    assert (runs[0].id, runs[0].raw_id, runs[0].optimizers) == (7, "abc", ["log"])


def test_reads_never_raise_and_never_open_the_breaker(httpx_mock):
    health(httpx_mock)
    for _ in range(10):
        httpx_mock.add_response(url=f"{ADDR}/sdk/v1/stats", status_code=500)
    rt = Runtime()
    for _ in range(10):
        assert rt.totals() == []
    assert rt.ready()


def test_reads_in_bypass_are_empty(monkeypatch):
    monkeypatch.setenv("GASCOIGNE_SDK", "off")
    rt = Runtime()
    assert rt.totals() == [] and rt.runs() == []


def test_bad_json_is_empty_not_an_error(httpx_mock):
    health(httpx_mock)
    httpx_mock.add_response(url=f"{ADDR}/sdk/v1/recent", text="<html>")
    assert Runtime().runs() == []


def test_settings_serialize_the_ledger():
    settings = Settings(ledger="memory")
    import json

    assert json.loads(settings.to_json()) == {"ledger": "memory"}
    assert json.loads(Settings().to_json()) == {}


@pytest.mark.skipif(not LIB.exists(), reason="build native/ first: mise run native:check")
def test_embedded_memory_ledger(monkeypatch, tmp_path):
    monkeypatch.setenv("GASCOIGNE_LIB", str(LIB))
    monkeypatch.setenv("GASCOIGNE_LEDGER", "")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    settings = Settings(ledger="memory", ignore_user_file=True)
    rt = Runtime(mode="native", settings=settings, agent="sdk", session="s1")
    raw = "INFO request served path=/api/items status=200 ms=12\n" * 400
    rt.optimize_result(raw, tool="bash", cmd="tail app.log")

    totals = rt.totals(by="agent")
    assert [(t.group, t.runs) for t in totals] == [("sdk", 1)] and totals[0].saved > 0
    runs = rt.runs(session="s1")
    assert len(runs) == 1 and runs[0].raw_id and runs[0].outcome == "optimized"
    # An unknown grouping is a bad query: empty, not an exception.
    assert rt.totals(by="nonsense") == []
    # Memory mode wrote no file.
    assert not list(tmp_path.iterdir())
    rt.close()
