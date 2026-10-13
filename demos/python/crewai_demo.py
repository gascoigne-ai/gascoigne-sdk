"""CrewAI: LiteLLM-style model id for OpenRouter."""

import common
import gascoigne
from crewai import LLM, Agent, Crew, Task
from crewai.tools import tool

common.rt("crewai")
wrapped = gascoigne.wrap_tool(common.search_logs)
search_logs = tool("search_logs")(wrapped)
llm = LLM(model=f"openrouter/{common.MODEL}", api_key=common.api_key())
agent = Agent(
    role="SRE",
    goal="Find what went wrong from logs",
    backstory="You read logs.",
    tools=[search_logs],
    llm=llm,
)
task = Task(description=common.PROMPT, expected_output="One sentence.", agent=agent)

if common.dry():
    common.dry_call(wrapped)
else:
    common.report(str(Crew(agents=[agent], tasks=[task]).kickoff()))
