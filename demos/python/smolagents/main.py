"""smolagents. Two added lines."""

import gascoigne

from demo_kit import PROMPT, openrouter, run, search_logs
from smolagents import CodeAgent, OpenAIServerModel, tool

# 1. Start gascoigne.
gascoigne.init(agent="smolagents")

# 2. Wrap the tool.
search_logs = gascoigne.wrap_tool(search_logs)

model = OpenAIServerModel(
    model_id=openrouter.model, api_base=openrouter.base_url, api_key=openrouter.api_key
)
agent = CodeAgent(tools=[tool(search_logs)], model=model)
run(lambda: agent.run(PROMPT), search_logs)
