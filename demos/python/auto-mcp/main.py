"""LangGraph with an MCP server: gascoigne decorates it after an explicit gascoigne.auto()."""

import asyncio
import sys
from pathlib import Path

import gascoigne
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

from demo_kit import PROMPT, openrouter, run

# 1. Start gascoigne.
gascoigne.init(agent="langgraph-mcp")

# 2. Opt in, explicitly: results of MCP calls and LangChain tools are now shortened. The tool that
# fetches originals is skipped, so asking for the full text does not shorten it again.
gascoigne.auto(skip=["retrieve_original"])

mcp_server = Path(__file__).with_name("server.py")
client = MultiServerMCPClient(
    {"logs": {"transport": "stdio", "command": sys.executable, "args": [str(mcp_server)]}}
)
tools = asyncio.run(client.get_tools()) + [tool(gascoigne.retrieve_original)]
agent = create_agent(
    ChatOpenAI(model=openrouter.model, api_key=openrouter.api_key, base_url=openrouter.base_url),
    tools,
)


async def ask() -> str:
    result = await agent.ainvoke({"messages": [("user", PROMPT)]})
    return result["messages"][-1].content


run(lambda: asyncio.run(ask()), lambda: asyncio.run(tools[0].ainvoke({})))
