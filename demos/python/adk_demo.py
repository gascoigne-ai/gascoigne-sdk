"""Google ADK: LiteLLM routes the model to OpenRouter."""

import asyncio
import os

import common
import gascoigne
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

common.rt("adk")
os.environ["OPENROUTER_API_KEY"] = common.api_key()
search_logs = gascoigne.wrap_tool(common.search_logs)
agent = Agent(
    name="logs",
    model=LiteLlm(model=f"openrouter/{common.MODEL}"),
    instruction="Answer from the tools.",
    tools=[search_logs],
)


async def main() -> None:
    sessions = InMemorySessionService()
    runner = Runner(agent=agent, app_name="demo", session_service=sessions)
    await sessions.create_session(app_name="demo", user_id="u", session_id="s")
    msg = types.Content(role="user", parts=[types.Part(text=common.PROMPT)])
    answer = ""
    async for ev in runner.run_async(user_id="u", session_id="s", new_message=msg):
        if ev.is_final_response() and ev.content:
            answer = ev.content.parts[0].text
    common.report(answer)


if common.dry():
    common.dry_call(search_logs)
else:
    asyncio.run(main())
