# Rules
- SDK code never raises into the host app and never blocks past its timeout: any failure returns the input.
- Missing CLI -> exactly one warning per process, then bypass; `base_url`s stay untouched.
- Core packages depend on nothing but an HTTP client; framework code is lazy-imported helpers or demos.
- Behavior shared by all languages lives in `spec/`; change it first, then every SDK.
- Secrets (API keys) only from the environment, never in code, demos or fixtures.
- New integration = helper (only if wrap_tool is not enough) + demo in `demos/` + test + README row.
- No competitor or other token-tool names in code, docs or commits.
- Tools come from `mise.toml`; Python through uv.
- Style (100 columns, comments above code, typed models) is in `code-style.md`; `mise run check` enforces what tools can.
- Automatic decoration of tools or MCP clients (`auto()`) is enabled only by an explicit call in the
  application. Never by an environment variable, an import side effect or a config file. It must be
  reversible (`undo()`), idempotent, skip errors, and never touch structured data code reads.
