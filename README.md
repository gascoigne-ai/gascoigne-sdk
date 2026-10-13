<div align="center">

# 🌘 gascoigne-sdk

**Your agent framework reads less. Nothing gets lost.**

Drop-in token optimization for tool results, in the languages and frameworks you already use.<br>
`99% off a noisy log` · `Python · TypeScript · Go · Java · .NET · Rust` · `14 framework demos`

</div>

---

```text
🐘 tool result · 12,025 tokens          🌘 model reads · 142 tokens
2026-10-13T12:00:00Z INFO worker-0 …    2026-10-13T12:00:00Z INFO worker-0 …
2026-10-13T12:00:01Z INFO worker-1 …    … 247 repeats of lines above
… 392 more lines                        2026-10-13T12:04:10Z ERROR db connection timeout after 30s
                                        … 148 repeats of lines above
📉 savings ██████████████████████████████ 99%   original kept: gascoigne raw ded3885c
```

The SDK finds the [`gascoigne`](https://github.com/gascoigne-ai/gascoigne-cli) CLI, starts its local
server, and shortens tool results before your model reads them. Originals stay one call away (`raw`).

**No CLI, no problem.** If `gascoigne` is not on `PATH` the SDK logs one warning and passes everything
through unchanged. It never throws into your app, and a failing server trips a circuit breaker.

## Start in two lines

```sh
mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne   # the CLI the SDK talks to
```

```python
import gascoigne
search_logs = gascoigne.wrap_tool(search_logs)      # any tool function returning str
```

## Pick your language

| | Install | Hook |
|---|---|---|
| **Python** | `uv add gascoigne` | `gascoigne.wrap_tool(fn)` · `gascoigne.ext.langchain.optimize_tools(tools)` |
| **TypeScript** | `pnpm add @gascoigne/sdk` | `wrapTool(fn)` · `@gascoigne/ai-sdk` → `wrapTools(tools)` |
| **Go** | `go get github.com/gascoigne-ai/gascoigne-sdk/go` | `rt.WrapTool(tool)` · `gascoigne.WrapFunc(rt, name, fn)` |
| **Java** | `ai.gascoigne:gascoigne` | `g.wrapTool(name, fn)` (LangChain4j, Spring AI tool bodies) |
| **.NET** | `dotnet add package Gascoigne` | `g.WrapTool(name, fn)` (Semantic Kernel, Microsoft.Extensions.AI) |
| **Rust** | `cargo add gascoigne` | `rt.wrap_tool(name, fn)` · `rt.optimize(text, &Attrs::tool(..))` |

Every SDK has the same surface: `optimize`, `raw`, `proxy_base_url`, `stats`, `wrap_tool`, and an
`on_result` observer. The contract is in [`spec/protocol.md`](spec/protocol.md).

## Demos (OpenRouter)

Each demo gives an agent a tool that returns a 400-line service log and prints the before/after.
Each main file is the integration: **two added lines** (start gascoigne, wrap the tool). The noisy tool,
OpenRouter settings and the report live in a small `kit` next to it.

```sh
cp .env.example .env        # put your OPENROUTER_API_KEY in it (the file is git-ignored)
```

| Language | Frameworks | Run |
|---|---|---|
| Python | LangChain · LangGraph · Agno · Google ADK · OpenAI Agents · CrewAI · LlamaIndex · Pydantic AI · smolagents | `cd demos/python && uv run --extra langgraph python langgraph_demo.py` |
| TypeScript | Vercel AI SDK · LangChain.js · OpenAI Agents JS · Mastra | `cd typescript && pnpm install && pnpm --filter gascoigne-ts-demos ai-sdk` |
| Go | langchaingo | `cd go/demos && go run ./langchaingo` |
| Rust | (no LLM) log optimizer | `cd rust && cargo run --example logs` |

No key yet? `GASCOIGNE_DEMO_DRY=1` builds each agent and calls its tool without the LLM, and
`mise run demo` does that for all of them.

## Settings

| Env | Effect |
|---|---|
| `GASCOIGNE_BIN` | path of the CLI instead of `PATH` lookup |
| `GASCOIGNE_SERVER_ADDR` | server address, default `127.0.0.1:7878` |
| `GASCOIGNE_SDK=off` / `GASCOIGNE_SERVER=off` | bypass silently |

Needs a CLI with the `/sdk/v1` API. To also trim what the framework's own LLM client sends, point it at
`proxy_base_url("openai")`; for OpenRouter set `receivers.httpproxy.openai: https://openrouter.ai/api`
in the gascoigne config.

## Develop

```sh
mise install        # every toolchain: uv, node, pnpm, go, java, maven, dotnet, rust
mise run check      # lint + tests for all six SDKs
mise run e2e        # against a real binary: GASCOIGNE_BIN=../gascoigne-cli/bin/gascoigne
```

Releases and registry credentials: [`docs/releasing.md`](docs/releasing.md). Rules for contributors:
[`.harness/rules.md`](.harness/rules.md).

## License

Apache-2.0.
