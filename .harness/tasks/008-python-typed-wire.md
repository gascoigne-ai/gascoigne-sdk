status: todo
kind: chore
commit: refactor(python): wire answers parse into typed models once
scope: python/gascoigne/src/gascoigne/models.py, python/gascoigne/src/gascoigne/runtime.py, python/gascoigne/tests/**, CHANGELOG.md
depends_on: 003-spec-fixtures

# Typed wire models for python

Parse wire JSON into typed models once at the edge, with no untyped maps past it. `Outcome` and `Route` become `StrEnum`, so string comparisons by users keep working. One dataclass per route.

## Model
One type per route answer; absence of a field only where the spec allows it. `recent` stays an ordered list.

## Acceptance
- Test first: decode every `spec/fixtures` file into the models.
- `mise run check` passes.
