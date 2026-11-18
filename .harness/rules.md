# Rules
Adds to the shared `common/rules.md` and `common/commit-style.md`.

- SDK code never raises into the host app and never blocks past its timeout: any failure returns the input.
- Missing CLI -> exactly one warning per process, then bypass; `base_url`s stay untouched.
- Core packages depend on nothing but an HTTP client (and the JSON library where the language has no
  built-in one); framework code is lazy-imported helpers or demos. A dependency outside the list below
  needs an explicit decision recorded here first.
- Behavior shared by all languages lives in `spec/`; change it first, then every SDK.
- New integration = helper (only if wrap_tool is not enough) + demo in `demos/` + test + README row.
- Tools come from `mise.toml`; Python through uv.
- Style (100 columns, comments above code, typed models) is in `code-style.md`; `make check` enforces what tools can.
- Automatic decoration of tools or MCP clients (`auto()`) is enabled only by an explicit call in the
  application. Never by an environment variable, an import side effect or a config file. It must be
  reversible (`undo()`), idempotent, skip errors, and never touch structured data code reads.

## Approved dependencies
HTTP and JSON are the only runtime needs. Each language has the exceptions listed, nothing else.

| Language | Approved | Notes |
|---|---|---|
| python | `httpx` | |
| typescript | `koffi` (optional) | peer dependency, embedded mode only; HTTP is built in |
| rust | `serde`, `serde_json`, `ureq`, `libloading` (optional) | `libloading` behind the `native` feature; `rust/native` also uses `flate2`, `sha2` to unpack the bundle |
| java | `jackson-databind`, `jna` | `jna` optional, embedded mode only; `spring-ai-model` only in the `spring-ai` module |
| dotnet | `Microsoft.Extensions.AI` | only in `Gascoigne.Extensions.AI`; HTTP and JSON are built in |
| go | none | standard library only |
