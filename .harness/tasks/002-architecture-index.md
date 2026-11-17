status: todo
kind: docs
commit: docs(harness): architecture index per language
scope: `.harness/architecture.md`, `.harness/architecture/**`, CLAUDE.md

# Architecture index

One map of each language's zones: core (runtime state and models), adapters (HTTP, server process, native library), framework helpers. Name the mixed responsibilities of `runtime.py` as the target of task 007. Link it from CLAUDE.md.

Model: unchanged.

## Acceptance
- Every SDK language appears in the map.
- `mise run check` passes.
