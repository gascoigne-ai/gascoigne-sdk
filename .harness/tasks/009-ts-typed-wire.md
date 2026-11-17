status: todo
kind: chore
commit: refactor(typescript): wire answers parse into typed models once
scope: typescript/packages/sdk/src/**, typescript/packages/sdk/test/**
depends_on: 003-spec-fixtures

# Typed wire models for typescript

Parse wire JSON into typed models once at the edge, with no untyped maps past it. `Outcome` and `Route` become string-literal unions; the `Wire` helpers in `index.ts` parse once.

## Model
One type per route answer; absence of a field only where the spec allows it. `recent` stays an ordered list.

## Acceptance
- Test first: decode every `spec/fixtures` file into the models.
- `mise run check` passes.
