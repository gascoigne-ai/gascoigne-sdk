<div align="center">

# gascoigne-sdk

**Your agent framework reads less. Nothing gets lost.**

Drop-in token optimization for tool results, in the languages and frameworks you already use.<br>
`99% off a noisy log`, `Python | TypeScript | Go | Java | .NET | Rust`, `17 framework demos`

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

How to install each one, and the minimal code: [`docs/install.md`](docs/install.md).


| | Install | Hook |
|---|---|---|
| **Python** | [wheel or git](docs/install.md#python) | `gascoigne.wrap_tool(fn)`; for LangChain tools `gascoigne.ext.langchain.optimize_tools(tools)` |
| **TypeScript** | [GitHub Packages](docs/install.md#typescript) | `wrapTool(fn)`; for Vercel AI SDK `wrapTools(tools)` from `@gascoigne-ai/ai-sdk` |
| **Go** | `go get github.com/gascoigne-ai/gascoigne-sdk/go@v0.1.0` ([notes](docs/install.md#go)) | `rt.WrapTool(tool)` or `gascoigne.WrapFunc(rt, name, fn)` |
| **Java** | `ai.gascoigne:gascoigne` on [GitHub Packages](docs/install.md#java) | `g.optimize(text, Attrs.tool(name))` inside Spring AI / LangChain4j tools, or `g.wrapTool(name, fn)` |
| **.NET** | `Gascoigne` on [GitHub Packages](docs/install.md#net) | `g.WrapTool(name, fn)` for Semantic Kernel and Microsoft.Extensions.AI tools |
| **Rust** | [git tag](docs/install.md#rust) | `rt.wrap_tool(name, fn)` or `rt.optimize(text, &Attrs::tool(..))` |

Every SDK has the same surface: `optimize`, `raw`, `proxy_base_url`, `stats`, `wrap_tool`, and an
`on_result` observer. The contract is in [`spec/protocol.md`](spec/protocol.md).

## Demos (OpenRouter)

All demos live in [`demos/`](demos/README.md), as `demos/<language>/<framework>/<mode>` with mode
`wrap`, `proxy` or `auto`. Each main file is the integration: one or two added lines. The noisy tool,
OpenRouter settings and the report live in a small `kit` next to it.

```sh
cp .env.example .env        # put your OPENROUTER_API_KEY in it (the file is git-ignored)
```

| Language | Frameworks | Run |
|---|---|---|
| Python | langchain, langgraph, agno, google-adk, openai-agents, crewai, llamaindex, pydantic-ai, smolagents | `cd demos/python && uv run --extra langgraph python langgraph/wrap.py` |
| TypeScript | Vercel AI SDK, LangChain.js, OpenAI Agents JS, Mastra | `cd demos/typescript && pnpm install && pnpm ai-sdk:wrap` |
| Java | Spring AI, LangChain4j | see [`demos/README.md`](demos/README.md) |
| .NET | Microsoft.Extensions.AI | `cd demos/dotnet && dotnet run --project microsoft-extensions-ai/wrap` |
| Go | langchaingo | `cd demos/go && go run ./langchaingo/wrap` |
| Rust | none (no LLM, optimizes a log) | `cd demos/rust/plain && cargo run` |

No key yet? `GASCOIGNE_DEMO_DRY=1` builds each agent and calls its tool without the LLM, and
`mise run demo` does that for all of them.

## Proxy mode: automatic, no tool wrapping

Wrapping a tool is explicit. The alternative is to point the framework's LLM client at the gascoigne
proxy: every tool result in every request is shortened, whatever produced it (your functions,
built-in tools, MCP servers), and no tool code changes.

```python
# 1. Start gascoigne.
gascoigne.init(agent="langgraph")

# 2. Send LLM traffic through the gascoigne proxy.
base_url = gascoigne.proxy_base_url("openai") or openrouter.base_url
agent = create_agent(ChatOpenAI(model=..., api_key=..., base_url=base_url), [tool(search_logs)])
```

`proxy_base_url` returns nothing when gascoigne is unavailable, so the `or` falls back to the real
endpoint. The proxy forwards to the upstream in the gascoigne config; the demos ship
[`demos/gascoigne.yaml`](demos/gascoigne.yaml) pointing it at OpenRouter and start a dedicated server.

| Language | Proxy demos (`<framework>/proxy`) |
|---|---|
| Python | langchain, langgraph, agno, google-adk, openai-agents, crewai, llamaindex, pydantic-ai, smolagents |
| TypeScript | ai-sdk, langchain, openai-agents, mastra |
| Java | `spring-ai/proxy` |
| Go | `langchaingo/proxy` |

`mise run demo:proxy` runs most of them, and the auto demos, for real with no API key, using a fake LLM
([`scripts/fake_llm.py`](scripts/fake_llm.py)) in place of OpenRouter.

When to use which: proxy mode needs a client whose base URL you can set and covers everything the
model reads; wrapping works with any provider and lets you pick tools one by one.

## Auto mode: decorate tools and MCP calls, when you ask for it

If you would rather not wrap each tool, one explicit call decorates the place every tool call goes
through. Nothing is decorated unless your code asks: no environment switch, no import side effect.

| Language | Opt in with | Covers |
|---|---|---|
| Python | `gascoigne.auto(skip=[...])` | MCP servers through any framework using the `mcp` client, and LangChain / LangGraph tools |
| Java (Spring AI) | `@EnableGascoigne(skip = ...)` from `gascoigne-spring-ai` | every `@Tool`, function callback and MCP tool (wraps `ToolCallingManager`) |
| .NET (Microsoft.Extensions.AI) | `.UseFunctionInvocation(configure: c => c.UseGascoigne(g))` from `Gascoigne.Extensions.AI` | every function the chat client invokes, MCP tools included |

```python
# Start gascoigne, then opt in. Nothing is decorated unless this line is in your code.
gascoigne.init(agent="my-app")
gascoigne.auto(skip=["write_file"])
```

What it follows: `skip` and `only` pick tools; results under `min_chars` never leave the process;
errors and structured data that code reads are untouched; Python's `handle.undo()` restores everything.

Shortened results end with a `gascoigne raw <id>` hint. Give the model a way to follow it by adding the
retrieve tool, and list it in `skip` so fetching an original does not shorten it again:
`gascoigne.retrieve_original` (Python), `RetrieveOriginalTool` (Spring AI),
`RetrieveOriginalFunction.Create(g)` (.NET). Demos: `demos/python/langgraph/auto.py`,
`demos/java/spring-ai/auto`, `demos/dotnet/microsoft-extensions-ai/auto`.

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

Releases and registry credentials: [`docs/releasing.md`](docs/releasing.md). npm, Maven and NuGet
packages are on GitHub Packages: [`docs/github-packages.md`](docs/github-packages.md). Install
guide: [`docs/install.md`](docs/install.md). Rules for contributors:
[`.harness/rules.md`](.harness/rules.md).

## License

Apache-2.0.
