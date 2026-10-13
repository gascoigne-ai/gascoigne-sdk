"""smolagents: OpenAI-compatible server model."""

import common
import gascoigne
from smolagents import CodeAgent, OpenAIServerModel, tool

common.rt()
wrapped = gascoigne.wrap_tool(common.search_logs)
search_logs = tool(wrapped)
model = OpenAIServerModel(
    model_id=common.MODEL, api_base=common.BASE_URL, api_key=common.api_key()
)
agent = CodeAgent(tools=[search_logs], model=model)

if common.dry():
    common.dry_call(wrapped)
else:
    print(agent.run(common.PROMPT))
    common.report()
