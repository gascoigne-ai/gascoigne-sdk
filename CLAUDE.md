# gascoigne-sdk

SDKs that embed gascoigne-cli token optimization into agent frameworks. Contract: `spec/protocol.md`
(server side: `gascoigne-cli/cmd/gascoigne/sdk.go`). Tools via `mise install`; Python via uv.

## Commands
- `make check` - lint, types, tests; must pass before done
- `make e2e` - against a real binary (`GASCOIGNE_BIN=...`)
- demos: `demos/python`, see README

Shared with the other gascoigne repos: submodule `.harness/common`.
@.harness/common/rules.md
@.harness/common/commit-style.md
@.harness/common/code-style.md
@.harness/common/architecture-style.md
@.harness/common/data-structures.md
@.harness/rules.md
@.harness/code-style.md

Architecture map per language: `.harness/architecture.md`. Update it in the same commit as structural changes.

Task queue: `.harness/tasks/`, run with `/task-loop` (verify: `make check`).
