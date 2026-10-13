"""OpenAI Agents SDK, chat completions via OpenRouter. Two added lines."""

import gascoigne
from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool, set_tracing_disabled
from openai import AsyncOpenAI

from demo_kit import PROMPT, openrouter, run, search_logs

gascoigne.init(agent="openai-agents")  # 1. start gascoigne
search_logs = gascoigne.wrap_tool(search_logs)  # 2. wrap the tool

set_tracing_disabled(True)
cfg = openrouter()
client = AsyncOpenAI(base_url=cfg.base_url, api_key=cfg.api_key)
agent = Agent(
    name="logs",
    model=OpenAIChatCompletionsModel(model=cfg.model, openai_client=client),
    tools=[function_tool(search_logs)],
)
run(lambda: Runner.run_sync(agent, PROMPT).final_output, search_logs)
