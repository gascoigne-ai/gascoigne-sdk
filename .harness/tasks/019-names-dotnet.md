status: todo
kind: chore
commit: refactor(dotnet): full parameter names
scope: dotnet/**, demos/dotnet/**, CHANGELOG.md
depends_on: 013-param-name-check

# Full parameter names in dotnet

Rename about 26 one-letter parameters and closure arguments. List renamed public parameters in CHANGELOG.md: keyword and named callers break. Behavior does not change.

Model: unchanged.

## Acceptance
- `python3 scripts/style.py --params` over this scope reports nothing.
- Tests unchanged.
- `mise run check` passes.
