status: todo
kind: chore
commit: refactor(go): full parameter names
scope: go/**, native/**, demos/go/**
depends_on: 013-param-name-check

# Full parameter names in go

Rename about 23 one-letter parameters and closure arguments. Behavior does not change.

Model: unchanged.

## Acceptance
- `python3 scripts/style.py --params` over this scope reports nothing.
- Tests unchanged.
- `mise run check` passes.
