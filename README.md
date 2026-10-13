<div align="center">

# gascoigne-sdk

**Your agent framework reads less. Nothing gets lost.**

Drop-in token optimization for tool results, in the languages and frameworks you already use.<br>
`99% off a noisy log`, `Python | TypeScript | Go | Java | .NET | Rust`, `16 framework demos`

</div>

---

```text
Tool result: 12,025 tokens         Model reads: 142 tokens
  2026-10-13T12:00:00Z INFO ...      2026-10-13T12:00:00Z INFO ...
  ... 393 more lines                 ... 247 repeats of lines above
                                     2026-10-13T12:04:10Z ERROR db connection timeout
Saved 99%: 12,025 -> 142 tokens. Original: gascoigne raw ded3885c
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
| **Python** | `uv add gascoigne` | `gascoigne.wrap_tool(fn)`; for LangChain tools `gascoigne.ext.langchain.optimize_tools(tools)` |
| **TypeScript** | `pnpm add @gascoigne/sdk` | `wrapTool(fn)`; for Vercel AI SDK `wrapTools(tools)` from `@gascoigne/ai-sdk` |
| **Go** | `go get github.com/gascoigne-ai/gascoigne-sdk/go` | `rt.WrapTool(tool)` or `gascoigne.WrapFunc(rt, name, fn)` |
| **Java** | `ai.gascoigne:gascoigne` | `g.optimize(text, Attrs.tool(name))` inside Spring AI / LangChain4j tools, or `g.wrapTool(name, fn)` |
| **.NET** | `dotnet add package Gascoigne` | `g.WrapTool(name, fn)` for Semantic Kernel and Microsoft.Extensions.AI tools |
| **Rust** | `cargo add gascoigne` | `rt.wrap_tool(name, fn)` or `rt.optimize(text, &Attrs::tool(..))` |

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
| Python | `langchain`, `langgraph`, `agno`, `google-adk`, `openai-agents`, `crewai`, `llamaindex`, `pydantic-ai`, `smolagents` (one folder each) | `cd demos/python && uv run --extra langgraph python langgraph/main.py` |
| TypeScript | Vercel AI SDK, LangChain.js, OpenAI Agents JS, Mastra | `cd typescript && pnpm install && pnpm --filter gascoigne-ts-demos ai-sdk` |
| Java | Spring AI, LangChain4j | `mvn -f java/pom.xml install -DskipTests && cd java/demos && mvn -q package && java -jar spring-ai/target/*.jar` |
| Go | langchaingo | `cd go/demos && go run ./langchaingo` |
| Rust | none (no LLM, optimizes a log) | `cd rust && cargo run --example logs` |

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
