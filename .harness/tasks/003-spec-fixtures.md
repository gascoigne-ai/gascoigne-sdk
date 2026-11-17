status: todo
kind: chore
commit: test(spec): fixtures of real CLI output for every route
scope: spec/fixtures/**, scripts/capture_fixtures.sh, spec/protocol.md

# Real output for the protocol

Capture `health`, `optimize` (optimized and skipped), `raw`, `stats` and `recent` from a real `gascoigne` server into `spec/fixtures/`. A README there records the CLI version and proto 1.

Model: unchanged.

## Acceptance
- Capture with `HOME` and `XDG_*` pointed at a temp dir and a free `GASCOIGNE_SERVER_ADDR`.
- `grep -r /home spec/fixtures` finds nothing.
- `spec/protocol.md` links the fixtures.
- `mise run check` passes.
