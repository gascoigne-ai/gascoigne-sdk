"""LangGraph: gascoigne shortens what the tool returns. Two added lines."""

import gascoigne
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from demo_kit import PROMPT, openrouter, run, search_logs

gascoigne.init(agent="langgraph")  # 1. start gascoigne
search_logs = gascoigne.wrap_tool(search_logs)  # 2. wrap the tool

cfg = openrouter()
agent = create_agent(
    ChatOpenAI(model=cfg.model, api_key=cfg.api_key, base_url=cfg.base_url), [tool(search_logs)]
)
run(lambda: agent.invoke({"messages": [("user", PROMPT)]})["messages"][-1].content, search_logs)
