"""smolagents. Two added lines."""

import gascoigne
from smolagents import CodeAgent, OpenAIServerModel, tool

from demo_kit import PROMPT, openrouter, run, search_logs

gascoigne.init(agent="smolagents")  # 1. start gascoigne
search_logs = gascoigne.wrap_tool(search_logs)  # 2. wrap the tool

cfg = openrouter()
model = OpenAIServerModel(model_id=cfg.model, api_base=cfg.base_url, api_key=cfg.api_key)
agent = CodeAgent(tools=[tool(search_logs)], model=model)
run(lambda: agent.run(PROMPT), search_logs)
