"""Google ADK through the gascoigne proxy: tools are not wrapped, one added line."""

import asyncio
import os

import gascoigne
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from demo_kit import PROMPT, openrouter, run_proxy, search_logs

# 1. Start gascoigne.
gascoigne.init(agent="google-adk")

# 2. Send LLM traffic through the gascoigne proxy.
base_url = gascoigne.proxy_base_url("openai") or openrouter.base_url

os.environ["OPENROUTER_API_KEY"] = openrouter.api_key
agent = Agent(
    name="logs",
    model=LiteLlm(model=f"openrouter/{openrouter.model}", api_base=base_url),
    tools=[search_logs],
)


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


run_proxy(lambda: asyncio.run(ask()))
