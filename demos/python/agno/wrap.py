"""Agno: any function is a tool. Two added lines."""

import gascoigne
from agno.agent import Agent
from agno.models.openrouter import OpenRouter

from demo_kit import PROMPT, openrouter, run, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="agno")

# 2. Wrap the tool.
search_logs = gascoigne.wrap_tool(search_logs)

agent = Agent(
    model=OpenRouter(id=openrouter.model, api_key=openrouter.api_key), tools=[search_logs]
)
run(lambda: agent.run(PROMPT).content, search_logs)
