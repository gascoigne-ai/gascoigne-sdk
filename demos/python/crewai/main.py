"""CrewAI. Two added lines."""

import gascoigne
from crewai.tools import tool

from crewai import LLM, Agent, Crew, Task
from demo_kit import PROMPT, openrouter, run, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="crewai")

# 2. Wrap the tool.
search_logs = gascoigne.wrap_tool(search_logs)

agent = Agent(
    role="SRE",
    goal="Find what went wrong from logs",
    backstory="You read logs.",
    tools=[tool("search_logs")(search_logs)],
    llm=LLM(model=f"openrouter/{openrouter.model}", api_key=openrouter.api_key),
)
task = Task(description=PROMPT, expected_output="One sentence.", agent=agent)
run(lambda: Crew(agents=[agent], tasks=[task]).kickoff(), search_logs)
