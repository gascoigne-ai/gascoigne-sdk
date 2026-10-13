"""smolagents through the gascoigne proxy: tools are not wrapped, one added line."""

import gascoigne

from demo_kit import PROMPT, openrouter, run_proxy, search_logs
from smolagents import OpenAIServerModel, ToolCallingAgent, tool

# 1. Start gascoigne.
gascoigne.init(agent="smolagents")

# 2. Send LLM traffic through the gascoigne proxy.
base_url = gascoigne.proxy_base_url("openai") or openrouter.base_url

model = OpenAIServerModel(model_id=openrouter.model, api_base=base_url, api_key=openrouter.api_key)
agent = ToolCallingAgent(tools=[tool(search_logs)], model=model)
run_proxy(lambda: agent.run(PROMPT))
