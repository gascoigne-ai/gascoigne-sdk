status: todo
kind: chore
commit: test(dotnet): client and ledger tests read the spec fixtures
scope: dotnet/tests/**
depends_on: 003-spec-fixtures

# dotnet tests read the spec fixtures

Replace handwritten JSON in `ClientTests.cs` and `LedgerTests.cs` with the real fixtures. Assertions stay the same.

Model: unchanged.

## Acceptance
- Assertions unchanged.
- `mise run check` passes.
