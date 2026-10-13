"""Pydantic AI: OpenRouter provider."""

import common
import gascoigne
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

common.rt("pydantic-ai")
search_logs = gascoigne.wrap_tool(common.search_logs)
model = OpenAIChatModel(common.MODEL, provider=OpenRouterProvider(api_key=common.api_key()))
agent = Agent(model, tools=[search_logs])

if common.dry():
    common.dry_call(search_logs)
else:
    common.report(str(agent.run_sync(common.PROMPT).output))
