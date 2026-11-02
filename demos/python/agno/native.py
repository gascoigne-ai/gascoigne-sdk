"""Agno, native: the engine runs inside this process. No server, no CLI."""

import gascoigne
from agno.agent import Agent
from agno.models.openrouter import OpenRouter

from demo_kit import PROMPT, openrouter, run, search_logs

# 1. Start gascoigne in native mode. It raises if libgascoigne cannot be found.
gascoigne.init(agent="agno", mode="native")

# 2. Wrap the tool.
search_logs = gascoigne.wrap_tool(search_logs)

agent = Agent(
    model=OpenRouter(id=openrouter.model, api_key=openrouter.api_key), tools=[search_logs]
)
run(lambda: agent.run(PROMPT).content, search_logs)
