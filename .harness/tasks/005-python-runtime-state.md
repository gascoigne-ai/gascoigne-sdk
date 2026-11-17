status: todo
kind: chore
commit: refactor(python): runtime state is an enum with a transition table
scope: python/gascoigne/src/gascoigne/**, python/gascoigne/tests/**
depends_on: 004-spec-runtime-states

# Python runtime state enum

`_warned`, `_available`, `_failures` and `_paused_until` change together and form an implicit state machine. Replace them with one `RuntimeState` and a table.

## Model
From task 004. The four fields are removed; open-until derives from the state.

## Acceptance
- Parametrized transition-table test first.
- Existing spec cases unchanged and green.
- `mise run check` passes.
