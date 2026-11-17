status: todo
kind: chore
commit: refactor(rust): full parameter names
scope: rust/**, demos/rust/**
depends_on: 013-param-name-check

# Full parameter names in rust

Rename about 25 one-letter parameters and closure arguments. Behavior does not change.

Model: unchanged.

## Acceptance
- `python3 scripts/style.py --params` over this scope reports nothing.
- Tests unchanged.
- `mise run check` passes.
