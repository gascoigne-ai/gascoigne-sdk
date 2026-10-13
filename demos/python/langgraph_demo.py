"""LangGraph: prebuilt ReAct agent."""

import common
from gascoigne.ext.langchain import optimize_tools
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

common.rt()
search_logs = tool(common.search_logs)
tools = optimize_tools([search_logs])
llm = ChatOpenAI(model=common.MODEL, base_url=common.BASE_URL, api_key=common.api_key())
agent = create_react_agent(llm, tools)

if common.dry():
    common.dry_call(lambda: search_logs.invoke({}))
else:
    result = agent.invoke({"messages": [("user", common.PROMPT)]})
    print(result["messages"][-1].content)
    common.report()
