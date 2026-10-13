"""Agno: any function is a tool."""

import common
import gascoigne
from agno.agent import Agent
from agno.models.openrouter import OpenRouter

common.rt()
search_logs = gascoigne.wrap_tool(common.search_logs)
agent = Agent(model=OpenRouter(id=common.MODEL, api_key=common.api_key()), tools=[search_logs])

if common.dry():
    common.dry_call(search_logs)
else:
    agent.print_response(common.PROMPT)
    common.report()
