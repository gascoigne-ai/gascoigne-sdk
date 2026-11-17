status: todo
kind: chore
commit: refactor(rust): wire answers parse into typed models once
scope: rust/src/**, rust/tests/**
depends_on: 003-spec-fixtures

# Typed wire models for rust

Parse wire JSON into typed models once at the edge, with no untyped maps past it. `lib.rs` stops using `serde_json::Value` at the boundary: one serde struct per route and an `Outcome` enum. `tests/runtime.rs` reads the fixtures.

## Model
One type per route answer; absence of a field only where the spec allows it. `recent` stays an ordered list.

## Acceptance
- Test first: decode every `spec/fixtures` file into the models.
- `mise run check` passes.
