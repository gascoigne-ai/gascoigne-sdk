"""LlamaIndex FunctionAgent. Two added lines."""

import asyncio

import gascoigne
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openrouter import OpenRouter

from demo_kit import PROMPT, openrouter, run, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="llamaindex")

# 2. Wrap the tool.
search_logs = gascoigne.wrap_tool(search_logs)

agent = FunctionAgent(
    tools=[search_logs], llm=OpenRouter(model=openrouter.model, api_key=openrouter.api_key)
)
run(lambda: asyncio.run(agent.run(PROMPT)), search_logs)
