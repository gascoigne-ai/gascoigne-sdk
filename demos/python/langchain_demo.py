"""LangChain: bind a tool, run the tool loop by hand."""

import common
from gascoigne.ext.langchain import optimize_tools
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

common.rt("langchain")
search_logs = tool(common.search_logs)
(search_logs,) = optimize_tools([search_logs])
llm = ChatOpenAI(model=common.MODEL, base_url=common.BASE_URL, api_key=common.api_key())
llm = llm.bind_tools([search_logs])

if common.dry():
    common.dry_call(lambda: search_logs.invoke({}))
else:
    msgs = [HumanMessage(common.PROMPT)]
    ai = llm.invoke(msgs)
    msgs.append(ai)
    for call in ai.tool_calls:
        msgs.append(ToolMessage(search_logs.invoke(call["args"]), tool_call_id=call["id"]))
    common.report(str(llm.invoke(msgs).content))
