status: todo
kind: chore
commit: test: pin retrieve helpers in go, python and dotnet
scope: go/gascoigne/tool_test.go, python/gascoigne/tests/test_retrieve.py, dotnet/tests/**

# Pin the retrieve helpers

`go/gascoigne/tool.go`, `python/gascoigne/src/gascoigne/retrieve.py` and `dotnet/src/Gascoigne.Extensions.AI/RetrieveOriginalFunction.cs` have no tests. Pin the current behavior with passing tests.

Model: unchanged.

## Acceptance
- Tests pass against unchanged source.
- `mise run check` passes.
