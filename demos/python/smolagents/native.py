"""smolagents, native: the engine runs inside this process. No server, no CLI."""

import gascoigne

from demo_kit import PROMPT, openrouter, run, search_logs
from smolagents import OpenAIServerModel, ToolCallingAgent, tool

# 1. Start gascoigne in native mode. It raises if libgascoigne cannot be found.
gascoigne.init(agent="smolagents", mode="native")

# 2. Wrap the tool.
search_logs = gascoigne.wrap_tool(search_logs)

model = OpenAIServerModel(
    model_id=openrouter.model, api_base=openrouter.base_url, api_key=openrouter.api_key
)
agent = ToolCallingAgent(tools=[tool(search_logs)], model=model)
run(lambda: agent.run(PROMPT), search_logs)
