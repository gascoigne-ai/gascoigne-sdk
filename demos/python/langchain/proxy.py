"""LangChain through the gascoigne proxy: tools are not wrapped, one added line."""

import gascoigne
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from demo_kit import PROMPT, openrouter, run_proxy, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="langchain")

# 2. Send LLM traffic through the gascoigne proxy.
base_url = gascoigne.proxy_base_url("openai") or openrouter.base_url

logs = tool(search_logs)
llm = ChatOpenAI(model=openrouter.model, api_key=openrouter.api_key, base_url=base_url).bind_tools(
    [logs]
)


def ask() -> str:
    msgs = [HumanMessage(PROMPT)]
    ai = llm.invoke(msgs)
    msgs += [ai] + [
        ToolMessage(logs.invoke(c["args"]), tool_call_id=c["id"]) for c in ai.tool_calls
    ]
    return llm.invoke(msgs).content


run_proxy(ask)
