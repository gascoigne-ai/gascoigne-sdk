"""Agno through the gascoigne proxy: tools are not wrapped, one added line."""

import gascoigne
from agno.agent import Agent
from agno.models.openrouter import OpenRouter

from demo_kit import PROMPT, openrouter, run_proxy, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="agno")

# 2. Send LLM traffic through the gascoigne proxy.
base_url = gascoigne.proxy_base_url("openai") or openrouter.base_url

agent = Agent(
    model=OpenRouter(id=openrouter.model, api_key=openrouter.api_key, base_url=base_url),
    tools=[search_logs],
)
run_proxy(lambda: agent.run(PROMPT).content)
