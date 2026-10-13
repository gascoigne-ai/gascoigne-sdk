"""CrewAI through the gascoigne proxy: tools are not wrapped, one added line."""

import gascoigne
from crewai.tools import tool

from crewai import LLM, Agent, Crew, Task
from demo_kit import PROMPT, openrouter, run_proxy, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="crewai")

# 2. Send LLM traffic through the gascoigne proxy.
base_url = gascoigne.proxy_base_url("openai") or openrouter.base_url

agent = Agent(
    role="SRE",
    goal="Find what went wrong from logs",
    backstory="You read logs.",
    tools=[tool("search_logs")(search_logs)],
    llm=LLM(model=f"openrouter/{openrouter.model}", api_key=openrouter.api_key, base_url=base_url),
)
task = Task(description=PROMPT, expected_output="One sentence.", agent=agent)
run_proxy(lambda: Crew(agents=[agent], tasks=[task]).kickoff())
