"""LlamaIndex through the gascoigne proxy: tools are not wrapped, one added line."""

import asyncio

import gascoigne
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai_like import OpenAILike

from demo_kit import PROMPT, openrouter, run_proxy, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="llamaindex")

# 2. Send LLM traffic through the gascoigne proxy.
base_url = gascoigne.proxy_base_url("openai") or openrouter.base_url

agent = FunctionAgent(
    tools=[search_logs],
    llm=OpenAILike(
        model=openrouter.model,
        api_key=openrouter.api_key,
        api_base=base_url,
        is_chat_model=True,
        is_function_calling_model=True,
    ),
)


async def ask() -> str:
    return str(await agent.run(PROMPT))


run_proxy(lambda: asyncio.run(ask()))
