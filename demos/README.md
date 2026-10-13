# Demos

One tree, one convention: `demos/<language>/<framework>/<mode>`.

| Mode | What it shows | Gascoigne code |
|---|---|---|
| `wrap` | The tool is wrapped explicitly. | `init` + wrap the tool |
| `proxy` | LLM traffic goes through the gascoigne proxy; tools are untouched. | `init` + `proxy_base_url` |
| `auto` | One explicit call decorates every tool and MCP call. | `init` + `auto()` / `@EnableGascoigne` |

```text
demos/
  gascoigne.yaml        # the proxy forwards to OpenRouter
  python/               # uv project; demo_kit/ is the shared helper
    <framework>/{wrap,proxy}.py        langchain langgraph agno google-adk openai-agents
                                       crewai llamaindex pydantic-ai smolagents
    langgraph/auto.py                  + mcp_server.py, the MCP server it talks to
  typescript/           # pnpm project; kit.ts is the shared helper
    <framework>/{wrap,proxy}.ts        ai-sdk langchain openai-agents mastra
  java/                 # Maven reactor; kit/ is the shared helper
    spring-ai/{wrap,proxy,auto}        langchain4j/wrap
  go/                   # Go module; kit/ is the shared helper
    langchaingo/{wrap,proxy}
  dotnet/               # kit/ is the shared helper
    microsoft-extensions-ai/{wrap,auto}
  rust/plain/wrap.rs    # no framework, no LLM
```

A demo's main file shows only the integration. Environment loading, OpenRouter settings, the noisy
tool and the report live in the language's `kit`, which you never need to open.

## Run

```sh
cp .env.example .env     # in the repo root; put your OPENROUTER_API_KEY in it
```

| Language | Run |
|---|---|
| Python | `cd demos/python && uv run --extra langgraph python langgraph/wrap.py` (`proxy.py`, `auto.py` the same way; for `auto.py` use `--extra auto-mcp`) |
| TypeScript | `cd demos/typescript && pnpm install && pnpm ai-sdk:wrap` (or `:proxy`) |
| Java | `mvn -f java/pom.xml install -DskipTests && mvn -f java/spring-ai/pom.xml install -DskipTests && cd demos/java && mvn -q package && java -jar spring-ai/wrap/target/demo-spring-ai-wrap-0.0.0.jar` |
| .NET | `cd demos/dotnet && dotnet run --project microsoft-extensions-ai/wrap` (or `auto`) |
| Go | `cd demos/go && go run ./langchaingo/wrap` |
| Rust | `cd demos/rust/plain && cargo run` |

No key yet? `GASCOIGNE_DEMO_DRY=1` builds each agent and calls its tool without the LLM
(`mise run demo` does that for all `wrap` demos), and `mise run demo:proxy` runs the `proxy` and
`auto` demos for real against a fake LLM.
