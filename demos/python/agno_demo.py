"""Agno: any function is a tool. Two added lines."""

import gascoigne
from agno.agent import Agent
from agno.models.openrouter import OpenRouter

from demo_kit import PROMPT, openrouter, run, search_logs

gascoigne.init(agent="agno")  # 1. start gascoigne
search_logs = gascoigne.wrap_tool(search_logs)  # 2. wrap the tool

cfg = openrouter()
agent = Agent(model=OpenRouter(id=cfg.model, api_key=cfg.api_key), tools=[search_logs])
run(lambda: agent.run(PROMPT).content, search_logs)
