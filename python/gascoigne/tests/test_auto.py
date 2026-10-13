import pytest
from gascoigne.retrieve import select
from gascoigne.runtime import PROTO, Runtime
from langchain_core.tools import tool
from mcp import Client
from mcp.server.mcpserver import MCPServer

import gascoigne

BIG = "line of noisy log output\n" * 100


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in ("GASCOIGNE_SDK", "GASCOIGNE_SERVER", "GASCOIGNE_BIN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GASCOIGNE_SERVER_ADDR", "127.0.0.1:9")


@pytest.fixture
def runtime(httpx_mock):
    httpx_mock.add_response(url="http://127.0.0.1:9/sdk/v1/health", json={"proto": PROTO})
    httpx_mock.add_response(
        url="http://127.0.0.1:9/sdk/v1/optimize",
        json={"text": "short [gascoigne: full: gascoigne raw abc]", "raw_id": "abc"},
        is_reusable=True,
    )
    return Runtime()


def server() -> MCPServer:
    mcp = MCPServer("logs")

    @mcp.tool()
    def search_logs() -> str:
        return BIG

    @mcp.tool()
    def write_file() -> str:
        return BIG

    return mcp


async def text_of(name: str) -> str:
    async with Client(server()) as client:
        result = await client.call_tool(name, {})
    return result.content[0].text


async def test_mcp_results_are_shortened_until_undone(runtime):
    handle = gascoigne.auto(runtime=runtime)
    assert "mcp" in handle.patched
    assert (await text_of("search_logs")).startswith("short")
    handle.undo()
    assert await text_of("search_logs") == BIG


async def test_skip_and_only(runtime):
    handle = gascoigne.auto(runtime=runtime, skip=["write_file"])
    assert await text_of("write_file") == BIG
    assert (await text_of("search_logs")).startswith("short")
    handle = gascoigne.auto(runtime=runtime, only=["write_file"])
    assert await text_of("search_logs") == BIG
    handle.undo()


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_small_results_never_leave_the_process(runtime, httpx_mock):
    handle = gascoigne.auto(runtime=runtime, min_chars=10_000)
    assert await text_of("search_logs") == BIG
    handle.undo()
    assert not [r for r in httpx_mock.get_requests() if r.url.path.endswith("optimize")]


def test_langchain_tools_are_shortened(runtime):
    @tool
    def search_logs() -> str:
        """Return the logs."""
        return BIG

    handle = gascoigne.auto(runtime=runtime)
    assert "langchain" in handle.patched
    assert search_logs.invoke({}).startswith("short")
    handle.undo()
    assert search_logs.invoke({}) == BIG


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_auto_twice_replaces_the_first(runtime):
    first = gascoigne.auto(runtime=runtime)
    second = gascoigne.auto(runtime=runtime)
    assert not first.patched and second.patched
    second.undo()


def test_select_narrows_the_original():
    text = "\n".join(f"row {i}" for i in range(1, 501))
    assert select(text, lines="2-3") == "2: row 2\n3: row 3"
    assert select(text, grep=r"row 4\d\d$").count("\n") == 99
    assert "more lines" in select(text)


async def test_structured_duplicate_is_shortened_with_the_text(runtime):
    handle = gascoigne.auto(runtime=runtime)
    async with Client(server()) as client:
        result = await client.call_tool("search_logs", {})
    handle.undo()
    assert result.content[0].text.startswith("short")
    assert result.structured_content == {"result": result.content[0].text}


def test_langchain_text_blocks_are_shortened(runtime):
    from langchain_core.tools import StructuredTool

    blocks = [{"type": "text", "text": BIG}, {"type": "image", "data": "x"}]
    structured = StructuredTool.from_function(lambda: blocks, name="blocks", description="d")
    handle = gascoigne.auto(runtime=runtime)
    out = structured.invoke({})
    handle.undo()
    assert out[0]["text"].startswith("short") and out[1] == blocks[1]
