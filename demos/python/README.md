# Python demos

See [`../README.md`](../README.md) for the layout. Here, each framework folder holds `wrap.py` and
`proxy.py`; `langgraph/` also has `auto.py` (an MCP server decorated by one explicit
`gascoigne.auto()` call). Shared code is in `demo_kit/`.

```sh
uv run --extra langgraph python langgraph/wrap.py
GASCOIGNE_DEMO_DRY=1 uv run --extra agno python agno/wrap.py     # no LLM call
uv run --extra auto-mcp python langgraph/auto.py
```

Extras (one per run, their pins conflict): `langchain langgraph agno adk openai-agents pydantic-ai
smolagents auto-mcp`.
