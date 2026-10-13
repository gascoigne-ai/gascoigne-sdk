"""LangChain: bind a tool and run the tool loop yourself. Two added lines."""

import gascoigne
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from demo_kit import PROMPT, openrouter, run, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="langchain")

# 2. Wrap the tool.
search_logs = gascoigne.wrap_tool(search_logs)

logs = tool(search_logs)
llm = ChatOpenAI(
    model=openrouter.model, api_key=openrouter.api_key, base_url=openrouter.base_url
).bind_tools([logs])


def ask() -> str:
    msgs = [HumanMessage(PROMPT)]
    ai = llm.invoke(msgs)
    msgs += [ai] + [
        ToolMessage(logs.invoke(c["args"]), tool_call_id=c["id"]) for c in ai.tool_calls
    ]
    return llm.invoke(msgs).content


run(ask, search_logs)
