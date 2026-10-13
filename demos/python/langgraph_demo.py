"""LangGraph: `create_agent` builds a LangGraph graph with a tool loop."""

import common
from gascoigne.ext.langchain import optimize_tools
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

common.rt("langgraph")
search_logs = tool(common.search_logs)
tools = optimize_tools([search_logs])
llm = ChatOpenAI(model=common.MODEL, base_url=common.BASE_URL, api_key=common.api_key())
agent = create_agent(llm, tools)

if common.dry():
    common.dry_call(lambda: search_logs.invoke({}))
else:
    result = agent.invoke({"messages": [("user", common.PROMPT)]})
    common.report(str(result["messages"][-1].content))
