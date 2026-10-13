import logging

import httpx
import pytest
from gascoigne.models import Stats
from gascoigne.runtime import PROTO, Runtime


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("GASCOIGNE_SDK", raising=False)
    monkeypatch.delenv("GASCOIGNE_SERVER", raising=False)
    monkeypatch.delenv("GASCOIGNE_BIN", raising=False)
    monkeypatch.setenv("GASCOIGNE_SERVER_ADDR", "127.0.0.1:9")


def test_missing_cli_warns_once_and_passes_through(monkeypatch, caplog):
    monkeypatch.setenv("PATH", "")
    rt = Runtime()
    with caplog.at_level(logging.WARNING, logger="gascoigne"):
        assert rt.optimize("hello " * 100) == "hello " * 100
        assert rt.optimize("again") == "again"
    warnings = [r for r in caplog.records if "not found on PATH" in r.message]
    assert len(warnings) == 1
    assert rt.proxy_base_url() is None
    assert rt.raw("x") == ""


def test_kill_switch(monkeypatch, caplog):
    monkeypatch.setenv("GASCOIGNE_SDK", "off")
    with caplog.at_level(logging.WARNING, logger="gascoigne"):
        assert Runtime().optimize("x") == "x"
    assert not caplog.records


def test_optimizes_through_server(httpx_mock):
    httpx_mock.add_response(
        url="http://127.0.0.1:9/sdk/v1/health", json={"version": "t", "proto": PROTO}
    )
    httpx_mock.add_response(
        url="http://127.0.0.1:9/sdk/v1/optimize",
        json={"text": "short", "raw_id": "abc", "raw_tokens": 100, "out_tokens": 5},
    )
    rt = Runtime(agent="demo")
    res = rt.optimize_result("long " * 100, tool="grep")
    assert (res.text, res.raw_id, res.out_tokens) == ("short", "abc", 5)
    sent = httpx.Request  # request body check
    body = httpx_mock.get_requests()[-1].content
    assert b'"agent":"demo"' in body.replace(b" ", b"") and b'"tool":"grep"' in body.replace(
        b" ", b""
    )
    assert sent
    assert rt.proxy_base_url("openai") == "http://127.0.0.1:9/v1"


def test_old_proto_bypasses(httpx_mock, monkeypatch):
    monkeypatch.setenv("PATH", "")
    httpx_mock.add_response(url="http://127.0.0.1:9/sdk/v1/health", json={"proto": 99})
    assert Runtime().optimize("x") == "x"


def test_failures_return_input_and_open_breaker(httpx_mock):
    httpx_mock.add_response(url="http://127.0.0.1:9/sdk/v1/health", json={"proto": PROTO})
    httpx_mock.add_response(
        url="http://127.0.0.1:9/sdk/v1/optimize", status_code=500, is_reusable=True
    )
    rt = Runtime()
    for _ in range(7):
        assert rt.optimize("text") == "text"
    posts = [r for r in httpx_mock.get_requests() if r.url.path.endswith("optimize")]
    # breaker opened after five failures
    assert len(posts) == 5


def test_wrap_tool_sync_and_async(httpx_mock):
    import asyncio

    httpx_mock.add_response(url="http://127.0.0.1:9/sdk/v1/health", json={"proto": PROTO})
    httpx_mock.add_response(
        url="http://127.0.0.1:9/sdk/v1/optimize", json={"text": "S"}, is_reusable=True
    )
    rt = Runtime()

    @rt.wrap_tool
    def a() -> str:
        return "big"

    @rt.wrap_tool
    async def b() -> str:
        return "big"

    @rt.wrap_tool
    def c() -> int:
        return 3

    assert a() == "S" and asyncio.run(b()) == "S" and c() == 3


def test_optimize_tools_wraps_func_and_coroutine(httpx_mock):
    from types import SimpleNamespace

    from gascoigne.ext.langchain import optimize_tools

    httpx_mock.add_response(url="http://127.0.0.1:9/sdk/v1/health", json={"proto": PROTO})
    httpx_mock.add_response(
        url="http://127.0.0.1:9/sdk/v1/optimize",
        json={"text": "S", "raw_tokens": 10, "out_tokens": 1},
        is_reusable=True,
    )
    rt = Runtime()
    tool = SimpleNamespace(name="t", func=lambda: "big", coroutine=None)
    (wrapped,) = optimize_tools([tool], rt)
    assert wrapped.func() == "S" and rt.stats() == Stats(10, 1)
