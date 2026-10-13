"""CrewAI. Two added lines."""

import gascoigne
from crewai import LLM, Agent, Crew, Task
from crewai.tools import tool

from demo_kit import PROMPT, openrouter, run, search_logs

gascoigne.init(agent="crewai")  # 1. start gascoigne
search_logs = gascoigne.wrap_tool(search_logs)  # 2. wrap the tool

cfg = openrouter()
agent = Agent(
    role="SRE",
    goal="Find what went wrong from logs",
    backstory="You read logs.",
    tools=[tool("search_logs")(search_logs)],
    llm=LLM(model=f"openrouter/{cfg.model}", api_key=cfg.api_key),
)
task = Task(description=PROMPT, expected_output="One sentence.", agent=agent)
run(lambda: Crew(agents=[agent], tasks=[task]).kickoff(), search_logs)
