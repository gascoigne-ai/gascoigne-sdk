# Rules
- SDK code never raises into the host app and never blocks past its timeout: any failure returns the input.
- Missing CLI → exactly one warning per process, then bypass; `base_url`s stay untouched.
- Core packages depend on nothing but an HTTP client; framework code is lazy-imported helpers or demos.
- Behavior shared by all languages lives in `spec/`; change it first, then every SDK.
- Secrets (API keys) only from the environment, never in code, demos or fixtures.
- New integration = helper (only if wrap_tool is not enough) + demo in `demos/` + test + README row.
- No competitor or other token-tool names in code, docs or commits.
- Tools come from `mise.toml`; Python through uv.
