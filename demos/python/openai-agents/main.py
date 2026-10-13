"""OpenAI Agents SDK, chat completions via OpenRouter. Two added lines."""

import gascoigne
from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool, set_tracing_disabled
from openai import AsyncOpenAI

from demo_kit import PROMPT, openrouter, run, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="openai-agents")

# 2. Wrap the tool.
search_logs = gascoigne.wrap_tool(search_logs)

set_tracing_disabled(True)
client = AsyncOpenAI(base_url=openrouter.base_url, api_key=openrouter.api_key)
agent = Agent(
    name="logs",
    model=OpenAIChatCompletionsModel(model=openrouter.model, openai_client=client),
    tools=[function_tool(search_logs)],
)
run(lambda: Runner.run_sync(agent, PROMPT).final_output, search_logs)
