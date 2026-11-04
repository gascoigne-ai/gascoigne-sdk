"""Ledger reads: totals, runs and costs, through the server and through the embedded library."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from gascoigne.models import Costs, Run, Total
from gascoigne.native import Pricing, Settings
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


def test_runs_and_costs_through_the_server(httpx_mock):
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
    httpx_mock.add_response(
        url=f"{ADDR}/sdk/v1/costs",
        json={
            "billing": "api",
            "first_read_usd": 0.5,
            "in_context_usd": 1.5,
            "rereads": 110,
            "savings": [
                {
                    "model": "m",
                    "source": "static",
                    "tokenizer": "o200k",
                    "tokens": 10,
                    "model_tokens": 10,
                    "first_read_usd": 0.5,
                    "in_context_usd": 1.5,
                }
            ],
        },
    )
    rt = Runtime()
    runs = rt.runs(session="s1", limit=5, before=9)
    assert [type(r) for r in runs] == [Run]
    assert (runs[0].id, runs[0].raw_id, runs[0].optimizers) == (7, "abc", ["log"])
    costs = rt.costs()
    assert isinstance(costs, Costs)
    assert (costs.billing, costs.in_context_usd, costs.savings[0].source) == ("api", 1.5, "static")


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
    assert rt.costs() == Costs()


def test_bad_json_is_empty_not_an_error(httpx_mock):
    health(httpx_mock)
    httpx_mock.add_response(url=f"{ADDR}/sdk/v1/recent", text="<html>")
    assert Runtime().runs() == []


def test_settings_serialize_ledger_and_pricing():
    settings = Settings(
        ledger="memory",
        pricing=Pricing(billing="subscription", prices={"m": {"in": 1, "out": 2}}, file="p.json"),
    )
    import json

    assert json.loads(settings.to_json()) == {
        "ledger": "memory",
        "pricing": {
            "billing": "subscription",
            "prices": {"m": {"in": 1, "out": 2}},
            "file": "p.json",
        },
    }
    assert json.loads(Settings().to_json()) == {}


@pytest.mark.skipif(not LIB.exists(), reason="build native/ first: mise run native:check")
def test_embedded_memory_ledger(monkeypatch, tmp_path):
    monkeypatch.setenv("GASCOIGNE_LIB", str(LIB))
    monkeypatch.setenv("GASCOIGNE_LEDGER", "")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    settings = Settings(
        ledger="memory",
        ignore_user_file=True,
        pricing=Pricing(prices={"acme-large": {"in": 3, "out": 15, "tokenizer": "claude"}}),
    )
    rt = Runtime(mode="native", settings=settings, agent="sdk", session="s1")
    raw = "INFO request served path=/api/items status=200 ms=12\n" * 400
    rt.optimize_result(raw, tool="bash", cmd="tail app.log", model="acme-large")

    totals = rt.totals(by="agent")
    assert [(t.group, t.runs) for t in totals] == [("sdk", 1)] and totals[0].saved > 0
    runs = rt.runs(session="s1")
    assert len(runs) == 1 and runs[0].raw_id and runs[0].outcome == "optimized"
    costs = rt.costs()
    assert costs.billing == "api" and costs.in_context_usd > 0
    assert costs.savings[0].source == "static"
    # An unknown grouping is a bad query: empty, not an exception.
    assert rt.totals(by="nonsense") == []
    # Memory mode wrote no file.
    assert not list(tmp_path.iterdir())
    rt.close()
