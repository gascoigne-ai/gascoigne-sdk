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
Python is split: `state.py` holds the state machine, `http.py` and `process.py` the two adapters,
`models.py` the wire types. `python/gascoigne/src/gascoigne/runtime.py` is now the composition
point, and what still mixes there is small:
- core: `Runtime` owns the `_lock` and the `_stats`, and drives the `Machine` from `state.py`;
- adapter logic: `_health` and `_start_server` decide events and warnings from `http.health` and
  `process.*`, with the 3 s poll loop; `_read` and `optimize_result` choose native or HTTP and
  catch `httpx.HTTPError` next to `NativeError`;
- helpers: `wrap_tool`, `proxy_base_url`, `retrieve`, and the module functions over a default
  instance (`init`, `optimize`, `raw`, `stats`, ...) live in the same file;
- query building (`_query`, `_rfc3339`) sits beside the request code.

Wire answers are parsed once in `models.py`, with one exception: `http.health()` reads `proto`
from the raw JSON and returns an int; the `Health` model exists but only tests use it.

The other languages still let the runtime type (`Runtime` in TypeScript, Rust and Go, `Gascoigne`
in Java, `GascoigneClient` in .NET) hold core state and both adapters together: breaker, warn-once
and stats sit beside the HTTP calls and the server spawn in one file. Java is the partial
exception: the stored state, transitions, breaker counters and warn-once flag moved into the
package-private `Machine`, but `Gascoigne.java` still holds the HTTP calls and the process spawn.
Wire answers are parsed at the edge: TypeScript by the `decode*` functions (`decodeHealth`,
`decodeResult`, `decodeTotals`, `decodeRuns`), Rust by `serde`.

## Style check
`scripts/style.py` (run by `make check`) checks 100 columns, trailing comments and ASCII, and
since task 020 also the one-letter parameter check over the sources from `git ls-files`
(tracked plus untracked, not ignored). `scripts/style.py --params <path>...` runs only the
parameter check on any file or directory, for ad-hoc use. Exemptions follow `common/rules.md`
(Naming): `_`, `i`, `j`, Go `t`/`b`/`f` on testing types.
