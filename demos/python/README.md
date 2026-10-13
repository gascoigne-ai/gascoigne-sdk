# Python demos

Each `*_demo.py` is the whole integration: **two added lines** (`gascoigne.init`, `gascoigne.wrap_tool`).
Everything else (env, OpenRouter settings, the noisy tool, the report) is in `demo_kit.py`.

```sh
cp ../../.env.example ../../.env      # then put your OPENROUTER_API_KEY in it
uv run --extra langgraph python langgraph_demo.py
GASCOIGNE_DEMO_DRY=1 uv run --extra agno python agno_demo.py    # no LLM call
```

Extras: `langchain langgraph agno adk openai-agents crewai llamaindex pydantic-ai smolagents`.
