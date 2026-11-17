status: todo
kind: docs
commit: docs(harness): approved deps, data-structures import, backlog
scope: CLAUDE.md, .harness/rules.md, .harness/backlog.md

# Harness docs match the shared harness

CLAUDE.md imports `@.harness/common/data-structures.md`. `.harness/rules.md` lists approved dependencies: python `httpx`; typescript `koffi` (optional); rust `serde`, `serde_json`, `ureq`, `libloading` (optional); java `jackson-databind`, `jna`; dotnet `Microsoft.Extensions.AI`; go none. The rule that core depends on nothing but an HTTP client keeps its text, and the Rust core deps are documented as per-language exceptions. New `.harness/backlog.md` records deferred items: Go and Java tests reading `spec/fixtures`, a native layer check in `mise check`, the relative `replace` in `native/go.mod` (blocked until the cli tags `inproc`), state tables for TS/Go/Rust/dotnet, layer checks for Python and TS (needs a new tool, needs approval).

Model: unchanged.

## Acceptance
- `grep data-structures CLAUDE.md` finds the import.
- Every dependency in the manifests is in the list.
- `mise run check` passes.
