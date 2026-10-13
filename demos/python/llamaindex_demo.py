"""LlamaIndex FunctionAgent. Two added lines."""

import asyncio

import gascoigne
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openrouter import OpenRouter

from demo_kit import PROMPT, openrouter, run, search_logs

gascoigne.init(agent="llamaindex")  # 1. start gascoigne
search_logs = gascoigne.wrap_tool(search_logs)  # 2. wrap the tool

cfg = openrouter()
agent = FunctionAgent(tools=[search_logs], llm=OpenRouter(model=cfg.model, api_key=cfg.api_key))
run(lambda: asyncio.run(agent.run(PROMPT)), search_logs)
