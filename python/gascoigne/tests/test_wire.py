"""Every spec fixture decodes into the typed wire models."""

import json
from pathlib import Path

import pytest
from gascoigne.models import Health, Outcome, Result, Route, Run, Total

FIXTURES = Path(__file__).parents[3] / "spec" / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text())


def test_every_json_fixture_is_covered():
    assert {p.name for p in FIXTURES.glob("*.json")} == {
        "health.json",
        "optimize_optimized.json",
        "optimize_skipped.json",
        "recent.json",
        "stats.json",
    }


def test_health():
    health = Health.from_json(load("health.json"))
    assert health == Health(version="0.11.0 (8478f54)", proto=1, proxy=True)


def test_optimized():
    result = Result.from_json(load("optimize_optimized.json"))
    assert result.raw_id == "a4e762ac"
    assert (result.raw_tokens, result.out_tokens, result.skipped) == (9200, 34, "")


def test_skipped():
    result = Result.from_json(load("optimize_skipped.json"))
    assert result.text == "ok" and result.raw_id == ""
    assert result.skipped == "1 tokens < min_tokens 200"


def test_stats():
    totals = Total.parse_list(load("stats.json"))
    assert [t.group for t in totals] == ["default", "-"]
    assert totals[0].saved == 9166 and totals[0].first.startswith("2026-")


def test_recent():
    runs = Run.parse_list(load("recent.json"))
    assert [r.id for r in runs] == [2, 1]
    bypassed, optimized = runs
    assert bypassed.outcome is Outcome.BYPASSED and bypassed.route is None
    assert bypassed.optimizers == [] and bypassed.reason
    assert optimized.outcome is Outcome.OPTIMIZED and optimized.route is Route.DEFAULT
    assert optimized.outcome == "optimized" and optimized.route == "default"
    assert optimized.optimizers[0] == "embedjson" and len(optimized.optimizers) == 28


@pytest.mark.parametrize("raw", ["", "x"])
def test_unknown_route_and_outcome_survive(raw):
    data = {**load("recent.json")[0], "route": "custom" + raw, "outcome": "new" + raw}
    run = Run.from_json(data)
    assert run.route == "custom" + raw and run.outcome == "new" + raw


@pytest.mark.parametrize(
    "parse, data",
    [
        (Result.from_json, {"raw_tokens": 1, "out_tokens": 1}),
        (Result.from_json, {"text": "a", "raw_tokens": "1", "out_tokens": 1}),
        (Total.from_json, {"group": "g"}),
        (Run.from_json, {"id": 1}),
        (Health.from_json, {"proto": 1}),
        (Total.parse_list, {"group": "g"}),
    ],
)
def test_malformed_bodies_raise(parse, data):
    with pytest.raises((KeyError, TypeError)):
        parse(data)
