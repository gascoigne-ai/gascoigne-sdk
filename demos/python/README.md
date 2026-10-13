# Python demos

One folder per framework; each `main.py` is the whole integration: **two added lines**
(`gascoigne.init`, `gascoigne.wrap_tool`). Everything else (env, OpenRouter settings, the noisy tool,
the report) is in the shared `demo_kit` package.

```text
langchain/  langgraph/  agno/  google-adk/  openai-agents/
crewai/     llamaindex/ pydantic-ai/  smolagents/
```

```sh
cp ../../.env.example ../../.env       # then put your OPENROUTER_API_KEY in it
uv run --extra langgraph python langgraph/main.py
GASCOIGNE_DEMO_DRY=1 uv run --extra agno python agno/main.py    # no LLM call
```

Each folder also has a `proxy.py`: the same agent through the gascoigne proxy, with the tool left
unwrapped (one added line). Needs a real run, so it has no dry mode.

```sh
uv run --extra langgraph python langgraph/proxy.py
```

Extras (one per run, their pins conflict): `langchain langgraph agno adk openai-agents crewai
llamaindex pydantic-ai smolagents`.
