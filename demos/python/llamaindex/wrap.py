"""LlamaIndex FunctionAgent. Two added lines."""

import asyncio

import gascoigne
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai_like import OpenAILike

from demo_kit import PROMPT, openrouter, run, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="llamaindex")

# 2. Wrap the tool.
search_logs = gascoigne.wrap_tool(search_logs)

agent = FunctionAgent(
    tools=[search_logs],
    llm=OpenAILike(
        model=openrouter.model,
        api_key=openrouter.api_key,
        api_base=openrouter.base_url,
        is_chat_model=True,
        is_function_calling_model=True,
    ),
)


async def ask() -> str:
    return str(await agent.run(PROMPT))


run(lambda: asyncio.run(ask()), search_logs)
