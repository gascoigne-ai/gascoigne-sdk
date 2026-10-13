"""Pydantic AI through the gascoigne proxy: tools are not wrapped, one added line."""

import gascoigne
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from demo_kit import PROMPT, openrouter, run_proxy, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="pydantic-ai")

# 2. Send LLM traffic through the gascoigne proxy.
base_url = gascoigne.proxy_base_url("openai") or openrouter.base_url

model = OpenAIChatModel(
    openrouter.model, provider=OpenAIProvider(base_url=base_url, api_key=openrouter.api_key)
)
agent = Agent(model, tools=[search_logs])
run_proxy(lambda: agent.run_sync(PROMPT).output)
