"""Pydantic AI, native: the engine runs inside this process. No server, no CLI."""

import gascoigne
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from demo_kit import PROMPT, openrouter, run, search_logs

# 1. Start gascoigne in native mode. It raises if libgascoigne cannot be found.
gascoigne.init(agent="pydantic-ai", mode="native")

# 2. Wrap the tool.
search_logs = gascoigne.wrap_tool(search_logs)

model = OpenAIChatModel(openrouter.model, provider=OpenRouterProvider(api_key=openrouter.api_key))
agent = Agent(model, tools=[search_logs])
run(lambda: agent.run_sync(PROMPT).output, search_logs)
