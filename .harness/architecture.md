# Architecture index
One map per language. Zones follow `common/architecture-style.md`; this repo has no `app` zone
(the host application is the composition root) and no layer-check script yet.

- **core**: runtime state (availability, failure breaker, warn-once flag, stats) and wire/domain
  models. Depends on nothing but the language runtime.
- **adapters**: HTTP client to the `/sdk/v1` server, spawn of `gascoigne server start`, and the
  native library loader (ABI in `spec/native.md`).
- **helpers**: framework glue, lazy-imported and optional: `wrap_tool`, `auto()`, LangChain,
  Spring AI, Microsoft.Extensions.AI, AI SDK.

Contract for all languages: `spec/protocol.md`, `spec/native.md`. Per-language maps:

| Language | Map |
|---|---|
| python | [architecture/python.md](architecture/python.md) |
| typescript | [architecture/typescript.md](architecture/typescript.md) |
| go | [architecture/go.md](architecture/go.md) |
| rust | [architecture/rust.md](architecture/rust.md) |
| java | [architecture/java.md](architecture/java.md) |
| dotnet | [architecture/dotnet.md](architecture/dotnet.md) |
| native library (Go, C ABI) | [architecture/native.md](architecture/native.md) |

## Known mixing
In every language the runtime type (a `Runtime`, `Gascoigne` or `GascoigneClient` class or struct)
holds core state and both adapters together. `python/gascoigne/src/gascoigne/runtime.py` is the
worst case and the target of task 007 (`007-python-runtime-split`): `Runtime` mixes
- core: breaker (`_failed`, `_paused_until`), warn-once, `_stats`, the `_lock`;
- HTTP adapter: `httpx` client (`_http`, `_healthy`, `_read`, optimize/raw/totals/runs requests);
- process adapter: `_start_server` (finds the CLI, spawns it);
- helpers: `wrap_tool`, `proxy_base_url`;
- module-level default instance functions (`init`, `optimize`, `raw`, `stats`, ...).

Task 007 splits it into state, HTTP and process. Update the Python map in the same commit.
