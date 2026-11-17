status: todo
kind: chore
commit: refactor(java): runtime state is an enum with a transition table
scope: java/src/**
depends_on: 004-spec-runtime-states

# Java runtime state enum

Same change as the Python task, at `Gascoigne.java` (the `warned` flag and friends).

## Model
From task 004.

## Acceptance
- JUnit transition-table test first.
- `mise run check` passes.
