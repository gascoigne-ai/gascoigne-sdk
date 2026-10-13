"""LlamaIndex: FunctionAgent with the OpenRouter LLM."""

import asyncio

import common
import gascoigne
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openrouter import OpenRouter

common.rt()
search_logs = gascoigne.wrap_tool(common.search_logs)
agent = FunctionAgent(
    tools=[search_logs],
    llm=OpenRouter(model=common.MODEL, api_key=common.api_key()),
    system_prompt="Answer from the tools.",
)

if common.dry():
    common.dry_call(search_logs)
else:
    print(asyncio.run(agent.run(common.PROMPT)))
    common.report()
