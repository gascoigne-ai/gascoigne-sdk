"""OpenAI Agents SDK through the gascoigne proxy: tools are not wrapped, one added line."""

import gascoigne
from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool, set_tracing_disabled
from openai import AsyncOpenAI

from demo_kit import PROMPT, openrouter, run_proxy, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="openai-agents")

# 2. Send LLM traffic through the gascoigne proxy.
base_url = gascoigne.proxy_base_url("openai") or openrouter.base_url

set_tracing_disabled(True)
client = AsyncOpenAI(base_url=base_url, api_key=openrouter.api_key)
agent = Agent(
    name="logs",
    model=OpenAIChatCompletionsModel(model=openrouter.model, openai_client=client),
    tools=[function_tool(search_logs)],
)
run_proxy(lambda: Runner.run_sync(agent, PROMPT).final_output)
