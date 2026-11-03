# Code style

Adds to the shared `common/code-style.md` (readability first, shape, errors, comments, docs, tests)
for every language in this repo.

## Layout
- **100 columns maximum**, for code, comments and docs alike. Linters and formatters are configured
  to 100 (`ruff`, Biome, `rustfmt`, `golangci-lint lll`, `.editorconfig`); `scripts/style.py` checks
  every source file.
- Break long calls one argument per line rather than squeezing; let the formatter decide.

## Comments
- **Comments go on their own line, above the code they describe.** No trailing comments.

  ```python
  # Start gascoigne once, before any tool runs.
  gascoigne.init(agent="langgraph")
  ```

  not `gascoigne.init(agent="langgraph")  # start gascoigne`.
- Numbered steps in demos are comments above the line: `# 1. Start gascoigne`.

## Errors
- The SDK never throws into the host app: catch at the boundary, return the input unchanged,
  log at debug. Warn once per process for configuration problems (missing CLI, wrong protocol).

## Demos
- **One tree: `demos/<language>/<framework>/<mode>`**, mode being `wrap`, `proxy`, `auto` or
  `native`. Framework folders use the framework's usual name, the same in every language. Shared helpers sit in the
  language's `kit` (`demo_kit/`, `kit.ts`, `kit/`), never inside a demo.
- **Plain ASCII in source and output.** No emojis, arrows, box-drawing characters, ANSI colors or
  typographic punctuation: demos are read by people, in any terminal or editor. Write `->`,
  `...`, `-`; label sections in words (`Tool result`, `Model reads`, `Saved 99%`).
- A demo's main file shows only the integration: the two gascoigne lines and the framework's
  own code. Env loading, OpenRouter settings, the noisy tool and the report live in the demo's
  `kit`, which readers never need to open.
- A demo is at most about 25 lines of code. If it grows, move the weight into the kit.
- Secrets come from the environment (`.env`, git-ignored), never from code.

## Tests
- Every SDK keeps the same cases: missing CLI warns once and passes through, kill switch,
  optimize through server, unknown protocol bypasses, five failures open the breaker, wrapper.
