"""Google ADK: LiteLLM routes the model to OpenRouter. Two added lines."""

import asyncio
import os

import gascoigne
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from demo_kit import PROMPT, openrouter, run, search_logs

gascoigne.init(agent="google-adk")  # 1. start gascoigne
search_logs = gascoigne.wrap_tool(search_logs)  # 2. wrap the tool

cfg = openrouter()
os.environ["OPENROUTER_API_KEY"] = cfg.api_key
agent = Agent(name="logs", model=LiteLlm(model=f"openrouter/{cfg.model}"), tools=[search_logs])


async def ask() -> str:
    sessions = InMemorySessionService()
    runner = Runner(agent=agent, app_name="demo", session_service=sessions)
    await sessions.create_session(app_name="demo", user_id="u", session_id="s")
    msg = types.Content(role="user", parts=[types.Part(text=PROMPT)])
    answer = ""
    async for ev in runner.run_async(user_id="u", session_id="s", new_message=msg):
        if ev.is_final_response() and ev.content:
            answer = ev.content.parts[0].text
    return answer


run(lambda: asyncio.run(ask()), search_logs)
