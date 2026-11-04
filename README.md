# 🌘 gascoigne-sdk

**Your agent framework reads less. Nothing gets lost.**

Your agent app pays for every line a tool returns, on every turn that follows. The gascoigne SDKs
shorten tool results before the model reads them, keep what the model acts on, and leave every
original one `raw` call away.

**99% off a noisy log** (12,425 → 145 tokens) · six languages, one surface · runs inside your
process or through a local server · never throws into your app

`Python · TypeScript · Go · Java · .NET · Rust` · `15 framework demos` · `native or proxy`

---

## Try it in 30 seconds

No API key, no code changes: run a demo agent's tool and see what the model would read.

```sh
go install github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne@latest      # the engine
git clone https://github.com/gascoigne-ai/gascoigne-sdk && cd gascoigne-sdk/demos/python
GASCOIGNE_DEMO_DRY=1 uv run --extra langgraph python langgraph/wrap.py
```

Prefer no CLI at all? Build the engine as a library once (`mise run native:build`) and run the
native variant of the same demo:

```sh
GASCOIGNE_LIB=../../native/dist/libgascoigne.so GASCOIGNE_DEMO_DRY=1 \
  uv run --extra langgraph python langgraph/native.py
```

## Why you will want it

- **Longer runs, smaller bills.** A log tail, a search result or a JSON dump stops eating the
  context window on every later turn.
- **No trade-off in what the model knows.** Errors, failures and anomalies are kept; the engine is
  the one the gascoigne CLI evaluates on 427 real outputs (81% fewer tokens overall).
- **Two lines, any framework.** Wrap a tool, point the LLM client at a local proxy, or opt in to
  decorating every tool call with one explicit `auto()`.
- **Safe by construction.** Any failure returns the input unchanged. No CLI or library on the
  machine means one warning and a pass-through, never an exception in your app.

## See it work

A tool returns about 400 log lines (12,425 tokens). The model reads this instead:

```text
+- Tool result: 12,425 tokens ------------------------------------------------+
| 2026-10-13T12:00:00Z INFO worker-0 handled request id=2665 status=200        |
| ... 393 more lines                                                           |
+------------------------------------------------------------------------------+
+- Model reads: 145 tokens ---------------------------------------------------+
| 2026-10-13T12:00:00Z INFO worker-0 handled request id=2665 status=200        |
| … 247 repeats of lines above                                                 |
| 2026-10-13T12:04:10Z ERROR db connection timeout after 30s (pool exhau       |
| 2026-10-13T12:04:10Z INFO worker-5 handled request id=2915 status=200        |
| … 148 repeats of lines above                                                 |
+------------------------------------------------------------------------------+
Saved 99%: 12,425 -> 145 tokens. Original: gascoigne raw f57a39e8
```

The error survives, the repeats fold, and the hint tells the model (or you) how to get the full
text. This is the output of `demos/python/langgraph/wrap.py` in dry mode. Other outputs save less:
a source diff or a short search result has little to cut. The numbers per tool are in the
[gascoigne README](https://github.com/gascoigne-ai/gascoigne-cli#the-numbers).

## Start in two lines

```python
import gascoigne

gascoigne.init(agent="my-app")
search_logs = gascoigne.wrap_tool(search_logs)      # any tool function returning str
```

Same surface in every language: `init`, `wrap_tool`, `optimize`, `raw`, `proxy_base_url`, `stats`
and an `on_result` observer (contract: [`spec/protocol.md`](spec/protocol.md)). Every SDK carries
the version of the CLI release it was built with (0.10.0).

| | Install | Hook |
|---|---|---|
| **Python** | [wheel or git](docs/install.md#python) | `gascoigne.wrap_tool(fn)`; LangChain tools: `gascoigne.ext.langchain.optimize_tools(tools)` |
| **TypeScript** | [tarballs or GitHub Packages](docs/install.md#typescript) | `wrapTool(fn)`; Vercel AI SDK: `wrapTools(tools)` from `@gascoigne-ai/ai-sdk` |
| **Go** | `go get github.com/gascoigne-ai/gascoigne-sdk/go@v0.10.0` ([notes](docs/install.md#go)) | `rt.WrapTool(tool)` or `gascoigne.WrapFunc(rt, name, fn)` |
| **Java** | [GitHub Packages](docs/install.md#java) | `g.optimize(text, Attrs.tool(name))` in Spring AI / LangChain4j tools, or `g.wrapTool(name, fn)` |
| **.NET** | [nupkg or GitHub Packages](docs/install.md#net) | `g.WrapTool(name, fn)` for Semantic Kernel and Microsoft.Extensions.AI tools |
| **Rust** | [git tag](docs/install.md#rust) | `rt.wrap_tool(name, fn)` or `rt.optimize(text, &Attrs::tool(..))` |

## Native or proxy

Every SDK reaches the engine in one of two ways (contract: [`spec/native.md`](spec/native.md)).
Choose with `GASCOIGNE_MODE=native|proxy` or in code; the explicit argument wins.

| | Native | Proxy (default) |
|---|---|---|
| What runs | the engine, inside your process, as `libgascoigne` | the local `gascoigne server`, over HTTP |
| Needs | the library | the [`gascoigne`](https://github.com/gascoigne-ai/gascoigne-cli) CLI |
| LLM proxy URL | none | `proxy_base_url("openai")` |
| Choose it when | one process, no daemon, lowest latency | the server is shared with agents, or the library cannot be loaded |

Native in code:

| Language | Native, in code | Loads the library with |
|---|---|---|
| Python | `init(mode="native", settings=Settings(set=[...]))` | ctypes (stdlib) |
| TypeScript | `init({ mode: "native", settings: { set: [...] } })` | `koffi` (optional peer) |
| Go | `gascoigne.New(Options{Backend: b})`, `b, _ := embedded.New(ctx, ...)` | in process, no library |
| Java | `Gascoigne.builder().embedded(Settings.defaults()).build()` | JNA (optional) |
| .NET | `new GascoigneOptions { Embedded = new EmbeddedSettings() }` | `NativeLibrary` |
| Rust | `Runtime::native("agent", Settings::default())?`, feature `native` | `libloading` |

The SDK stays thin and never carries the library. Native mode looks in `$GASCOIGNE_LIB`, then the
system directories (`/usr/local/lib`, `~/.local/lib`, …), then an optional per-platform package, and
raises an error listing where it looked. Config stays in the library: its defaults, your user file,
then what you pass.

| Language | Optional native package | Picked |
|---|---|---|
| Python | `gascoigne-native` | pip, by platform |
| TypeScript | `@gascoigne-ai/sdk-native` (and `koffi`) | npm, by `os` and `cpu` |
| Go | `gascoigne-sdk/native/embedded` | engine linked in |
| Java | `ai.gascoigne:gascoigne-native`, classifier of your system (and `jna`) | you |
| .NET | `Gascoigne.Native.<rid>` | you |
| Rust | `gascoigne-native` | Cargo, by target |

## Read your savings

Every SDK can read what the engine recorded, so your app can show it or log it. Reads never raise and
return nothing on any failure (Go returns an error as well).

| Language | Tokens saved per group | Recent runs | What it is worth |
|---|---|---|---|
| Python | `rt.totals(by="day")` | `rt.runs(session="s1")` | `rt.costs()` |
| TypeScript | `await rt.totals({ by: "day" })` | `await rt.runs({ session })` | `await rt.costs()` |
| Go | `rt.Totals(ctx, TotalsQuery{By: "day"})` | `rt.Runs(ctx, RunsQuery{})` | `rt.Costs(ctx, TotalsQuery{})` |
| Java | `g.totals(TotalsQuery.builder().by("day").build())` | `g.runs(RunsQuery.ALL)` | `g.costs(TotalsQuery.ALL)` |
| .NET | `await g.TotalsAsync(new TotalsQuery { By = "day" })` | `await g.RunsAsync()` | `await g.CostsAsync()` |
| Rust | `rt.totals(&TotalsQuery { by: "day".into(), ..Default::default() })` | `rt.runs(&RunsQuery::default())` | `rt.costs(&TotalsQuery::default())` |

In proxy mode they read the ledger of your `gascoigne server`, the one its dashboard shows. In native
mode they read the engine's own ledger: the sqlite file by default, or `ledger: memory` (Python
`Settings(ledger="memory")`, TypeScript `settings: { ledger: "memory" }`, Go `embedded.Options{Ledger:
"memory"}`, Java `Settings.defaults().withLedger("memory")`, .NET `Ledger = "memory"`, Rust
`ledger: "memory".into()`) to keep it in your process, with no file.

`costs` is an estimate from list prices, not a bill. For your own prices, or none (`billing:
"subscription"` for a flat plan), pass `pricing` in the same settings: `prices` per model, in dollars per
million tokens, and an optional price sheet `file` (see [`spec/native.md`](spec/native.md#pricing)). In
proxy mode set them with `gascoigne pricing` on the machine that runs the server.

## Three ways to meet your tools

**Wrap** a tool: works with any provider, you pick tools one by one.

**Proxy**: point the framework's LLM client at gascoigne, and every tool result in every request is
shortened (your functions, built-in tools, MCP servers) with no tool code changes.

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
Proxy mode needs a client whose base URL you can set and covers everything the model reads.

**Auto**: one explicit call decorates the place every tool call goes through. Nothing is decorated
unless your code asks: no environment switch, no import side effect.

| Language | Opt in with | Covers |
|---|---|---|
| Python | `gascoigne.auto(skip=[...])` | MCP servers through any framework using the `mcp` client, and LangChain / LangGraph tools |
| Java (Spring AI) | `@EnableGascoigne(skip = ...)` from `gascoigne-spring-ai` | every `@Tool`, function callback and MCP tool (wraps `ToolCallingManager`) |
| .NET (Microsoft.Extensions.AI) | `.UseFunctionInvocation(configure: c => c.UseGascoigne(g))` from `Gascoigne.Extensions.AI` | every function the chat client invokes, MCP tools included |

`skip` and `only` pick tools; results under `min_chars` never leave the process; errors and
structured data that code reads are untouched; Python's `handle.undo()` restores everything.
Shortened results end with a `gascoigne raw <id>` hint. Give the model a way to follow it by adding the
retrieve tool, and list it in `skip` so fetching an original does not shorten it again:
`gascoigne.retrieve_original` (Python), `RetrieveOriginalTool` (Spring AI),
`RetrieveOriginalFunction.Create(g)` (.NET).

## Demos

Fifteen working agents in [`demos/`](demos/README.md), laid out as `demos/<language>/<framework>/<mode>`
with mode `wrap`, `proxy`, `auto` or `native`. Each is a main file plus the two lines that add
gascoigne. They call OpenRouter:

```sh
cp .env.example .env        # put your OPENROUTER_API_KEY in it (the file is git-ignored)
```

| Language | Frameworks | Run |
|---|---|---|
| Python | langchain, langgraph, agno, google-adk, openai-agents, pydantic-ai, smolagents | `cd demos/python && uv run --extra langgraph python langgraph/wrap.py` |
| TypeScript | Vercel AI SDK, LangChain.js, OpenAI Agents JS, Mastra | `cd demos/typescript && pnpm install && pnpm ai-sdk:wrap` |
| Java | Spring AI, LangChain4j | see [`demos/README.md`](demos/README.md) |
| .NET | Microsoft.Extensions.AI | `cd demos/dotnet && dotnet run --project microsoft-extensions-ai/wrap` |
| Go | langchaingo | `cd demos/go && go run ./langchaingo/wrap` |
| Rust | none (no LLM, optimizes a log) | `cd demos/rust/plain && cargo run` |

| Mode | Where |
|---|---|
| `wrap` | every framework above |
| `proxy` | Python (all seven), TypeScript (all four), `spring-ai/proxy`, `langchaingo/proxy` |
| `auto` | `python/langgraph/auto.py`, `java/spring-ai/auto`, `dotnet/microsoft-extensions-ai/auto` |
| `native` | Python (all seven), TypeScript (all four), `java/spring-ai/native`, `java/langchain4j/native`, `dotnet/microsoft-extensions-ai/native`, `rust/plain` (`--bin native`), `native/examples/plain` (Go) |

Run native demos with `GASCOIGNE_LIB=native/dist/libgascoigne.so` (`mise run native:build`).
No key yet? `GASCOIGNE_DEMO_DRY=1` builds each agent and calls its tool without the LLM, and
`mise run demo` does that for all of them; `mise run demo:proxy` runs the proxy and auto demos for
real with a fake LLM ([`scripts/fake_llm.py`](scripts/fake_llm.py)) in place of OpenRouter.

## Settings

| Env | Effect |
|---|---|
| `GASCOIGNE_MODE` | `native` or `proxy` (default) |
| `GASCOIGNE_LIB` | path of `libgascoigne` for native mode |
| `GASCOIGNE_LIB_PATH` | extra directories to search for it |
| `GASCOIGNE_LIB_DIR` / `GASCOIGNE_UNPACK=off` | where a bundled library unpacks / skip unpacking |
| `GASCOIGNE_BIN` | path of the CLI instead of `PATH` lookup (proxy mode) |
| `GASCOIGNE_SERVER_ADDR` | server address, default `127.0.0.1:7878` (proxy mode) |
| `GASCOIGNE_SDK=off` / `GASCOIGNE_SERVER=off` | bypass silently |

Proxy mode needs a CLI with the `/sdk/v1` API. To also trim what the framework's own LLM client
sends, point it at `proxy_base_url("openai")`; for OpenRouter set
`receivers.httpproxy.openai: https://openrouter.ai/api` in the gascoigne config.

## Documentation

[Install guide](docs/install.md) · [native library](spec/native.md) · [wire protocol](spec/protocol.md) ·
[changelog](CHANGELOG.md) · [releasing](docs/releasing.md) · [verifying a download](docs/verifying.md) ·
[GitHub Packages](docs/github-packages.md) · [website](https://gascoigne-ai.github.io/sdk/)

## Develop

```sh
mise install        # every toolchain: uv, node, pnpm, go, java, maven, dotnet, rust
mise run check      # lint + tests for all six SDKs
mise run e2e        # against a real binary: GASCOIGNE_BIN=../gascoigne-cli/bin/gascoigne
```

Rules for contributors: [`.harness/rules.md`](.harness/rules.md).

## License

[Apache License 2.0](LICENSE).
