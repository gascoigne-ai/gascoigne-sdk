"""Pydantic AI with the OpenRouter provider. Two added lines."""

import gascoigne
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from demo_kit import PROMPT, openrouter, run, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="pydantic-ai")

# 2. Wrap the tool.
search_logs = gascoigne.wrap_tool(search_logs)

model = OpenAIChatModel(openrouter.model, provider=OpenRouterProvider(api_key=openrouter.api_key))
agent = Agent(model, tools=[search_logs])
run(lambda: agent.run_sync(PROMPT).output, search_logs)
