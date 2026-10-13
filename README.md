# gascoigne-sdk

Embed [gascoigne](https://github.com/gascoigne-ai/gascoigne-cli) token optimization in apps built on
agent frameworks. The SDK finds the `gascoigne` CLI, starts its background server, and shortens tool
results before your model reads them (originals stay retrievable with `raw`).

**No CLI, no problem:** if `gascoigne` is not on `PATH` the SDK logs one warning and passes everything
through unchanged. It never raises into your app.

```sh
mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne   # the CLI the SDK talks to
uv add gascoigne                                                      # Python SDK
```

```python
import gascoigne

gascoigne.init(agent="my-app")
search_logs = gascoigne.wrap_tool(search_logs)    # any callable returning str, sync or async
```

| Language | Status | Where |
|---|---|---|
| Python (uv) | core + LangChain/LangGraph helper, demos for 9 frameworks | `python/` |
| TypeScript, Go | planned | |
| Java, .NET, Rust | planned | |

## Demos (OpenRouter)

LangChain · LangGraph · Agno · Google ADK · OpenAI Agents · CrewAI · LlamaIndex · Pydantic AI · smolagents.
Each gives an agent a tool that returns a 400-line log and prints the token savings.

```sh
export OPENROUTER_API_KEY=sk-or-...            # key stays in the environment
export OPENROUTER_MODEL=openai/gpt-4o-mini     # optional
cd demos/python
uv run --extra langgraph python langgraph_demo.py
GASCOIGNE_DEMO_DRY=1 uv run --extra agno python agno_demo.py   # builds the agent, skips the LLM call
```

Extras: `langchain langgraph agno adk openai-agents crewai llamaindex pydantic-ai smolagents`
(one per run: their pins conflict).

## Settings

| Env | Effect |
|---|---|
| `GASCOIGNE_BIN` | path of the CLI instead of `PATH` lookup |
| `GASCOIGNE_SERVER_ADDR` | server address, default `127.0.0.1:7878` |
| `GASCOIGNE_SDK=off` / `GASCOIGNE_SERVER=off` | bypass silently |

Protocol: [`spec/protocol.md`](spec/protocol.md). Needs a CLI with the `/sdk/v1` API.

## Develop

```sh
mise install && mise run check
GASCOIGNE_BIN=../gascoigne-cli/bin/gascoigne mise run e2e
```

## License

Apache-2.0.
