status: todo
kind: chore
commit: refactor(java): full parameter names
scope: java/**, demos/java/**
depends_on: 013-param-name-check

# Full parameter names in java

Rename about 36 one-letter parameters and closure arguments. Behavior does not change.

Model: unchanged.

## Acceptance
- `python3 scripts/style.py --params` over this scope reports nothing.
- Tests unchanged.
- `mise run check` passes.
