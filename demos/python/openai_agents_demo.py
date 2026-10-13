"""OpenAI Agents SDK: chat-completions model pointed at OpenRouter."""

import common
import gascoigne
from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    Runner,
    function_tool,
    set_tracing_disabled,
)
from openai import AsyncOpenAI

common.rt()
set_tracing_disabled(True)
wrapped = gascoigne.wrap_tool(common.search_logs)
search_logs = function_tool(wrapped)
client = AsyncOpenAI(base_url=common.BASE_URL, api_key=common.api_key())
agent = Agent(
    name="logs",
    model=OpenAIChatCompletionsModel(model=common.MODEL, openai_client=client),
    tools=[search_logs],
)

if common.dry():
    common.dry_call(wrapped)
else:
    print(Runner.run_sync(agent, common.PROMPT).final_output)
    common.report()
