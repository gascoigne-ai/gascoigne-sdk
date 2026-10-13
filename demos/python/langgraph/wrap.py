"""LangGraph: gascoigne shortens what the tool returns. Two added lines."""

import gascoigne
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from demo_kit import PROMPT, openrouter, run, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="langgraph")

# 2. Wrap the tool.
search_logs = gascoigne.wrap_tool(search_logs)

agent = create_agent(
    ChatOpenAI(model=openrouter.model, api_key=openrouter.api_key, base_url=openrouter.base_url),
    [tool(search_logs)],
)
run(lambda: agent.invoke({"messages": [("user", PROMPT)]})["messages"][-1].content, search_logs)
