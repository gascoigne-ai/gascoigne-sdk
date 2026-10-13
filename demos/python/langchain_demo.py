"""LangChain: bind a tool and run the tool loop yourself. Two added lines."""

import gascoigne
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from demo_kit import PROMPT, openrouter, run, search_logs

gascoigne.init(agent="langchain")  # 1. start gascoigne
search_logs = gascoigne.wrap_tool(search_logs)  # 2. wrap the tool

logs = tool(search_logs)
cfg = openrouter()
llm = ChatOpenAI(model=cfg.model, api_key=cfg.api_key, base_url=cfg.base_url).bind_tools([logs])


def ask() -> str:
    msgs = [HumanMessage(PROMPT)]
    ai = llm.invoke(msgs)
    msgs += [ai] + [ToolMessage(logs.invoke(c["args"]), tool_call_id=c["id"]) for c in ai.tool_calls]
    return llm.invoke(msgs).content


run(ask, search_logs)
