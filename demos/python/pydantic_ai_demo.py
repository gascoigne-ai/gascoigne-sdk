"""Pydantic AI with the OpenRouter provider. Two added lines."""

import gascoigne
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from demo_kit import PROMPT, openrouter, run, search_logs

gascoigne.init(agent="pydantic-ai")  # 1. start gascoigne
search_logs = gascoigne.wrap_tool(search_logs)  # 2. wrap the tool

cfg = openrouter()
model = OpenAIChatModel(cfg.model, provider=OpenRouterProvider(api_key=cfg.api_key))
agent = Agent(model, tools=[search_logs])
run(lambda: agent.run_sync(PROMPT).output, search_logs)
