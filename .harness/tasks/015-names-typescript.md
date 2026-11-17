status: todo
kind: chore
commit: refactor(typescript): full parameter names
scope: typescript/packages/**, demos/typescript/**
depends_on: 013-param-name-check

# Full parameter names in typescript

Rename about 26 one-letter parameters and closure arguments. Behavior does not change.

Model: unchanged.

## Acceptance
- `python3 scripts/style.py --params` over this scope reports nothing.
- Tests unchanged.
- `mise run check` passes.
