"""LangGraph through the gascoigne proxy: tools are not wrapped, one added line."""

import gascoigne
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from demo_kit import PROMPT, openrouter, run_proxy, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="langgraph")

# 2. Send LLM traffic through the gascoigne proxy.
base_url = gascoigne.proxy_base_url("openai") or openrouter.base_url

agent = create_agent(
    ChatOpenAI(model=openrouter.model, api_key=openrouter.api_key, base_url=base_url),
    [tool(search_logs)],
)
run_proxy(lambda: agent.invoke({"messages": [("user", PROMPT)]})["messages"][-1].content)
