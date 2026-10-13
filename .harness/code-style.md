# Code style

Applies to every language in this repo. Readability first: if a reader has to pause, rewrite.

## Layout
- **100 columns maximum**, for code, comments and docs alike. Linters and formatters are configured
  to 100 (`ruff`, Biome, `rustfmt`, `golangci-lint lll`, `.editorconfig`); `scripts/style.sh` checks
  every source file.
- Break long calls one argument per line rather than squeezing; let the formatter decide.

## Comments
- **Comments go on their own line, above the code they describe.** No trailing comments.

  ```python
  # Start gascoigne once, before any tool runs.
  gascoigne.init(agent="langgraph")
  ```

  not `gascoigne.init(agent="langgraph")  # start gascoigne`.
- Say why, not what. If the code needs a "what" comment, rename or split instead.
- Public API gets a doc comment in the language's own form (docstring, TSDoc, Go doc, Javadoc,
  XML doc, rustdoc), starting with what the thing is or does.
- Numbered steps in demos are comments above the line: `# 1. Start gascoigne`.
- No commented-out code. No TODO without an issue or backlog entry.

## Data
- **Typed models, never ad-hoc dictionaries.** Wire bodies, settings, results and stats are
  dataclasses / interfaces / structs / records, with serialization attributes where needed.
  A `dict` / `map` / `Dictionary` is for genuinely dynamic keys only.
- Use named constants for protocol numbers, timeouts and thresholds.
- Prefer enums or small types over magic strings for states.

## Structure
- Early returns; keep the happy path flat. At most two levels of nesting.
- Small functions that do one thing. A function that needs a section comment wants splitting.
- Three similar lines beat a premature abstraction.
- Names are short and exact; wide scopes get full words.

## Errors
- The SDK never throws into the host app: catch at the boundary, return the input unchanged,
  log at debug. Warn once per process for configuration problems (missing CLI, wrong protocol).
- Do not swallow errors silently elsewhere; wrap with context.

## Demos
- **Plain ASCII in source and output.** No emojis, arrows, box-drawing characters, ANSI colors or
  typographic punctuation: demos are read by people, in any terminal or editor. Write `->`,
  `...`, `-`; label sections in words (`Tool result`, `Model reads`, `Saved 99%`).
- A demo's main file shows only the integration: the two gascoigne lines and the framework's
  own code. Env loading, OpenRouter settings, the noisy tool and the report live in the demo's
  `kit`, which readers never need to open.
- A demo is at most about 25 lines of code. If it grows, move the weight into the kit.
- Secrets come from the environment (`.env`, git-ignored), never from code.

## Tests
- Behavior, not implementation. Stub the server with the language's standard HTTP test tools,
  no mocking frameworks beyond what the ecosystem expects.
- Every SDK keeps the same cases: missing CLI warns once and passes through, kill switch,
  optimize through server, unknown protocol bypasses, five failures open the breaker, wrapper.
