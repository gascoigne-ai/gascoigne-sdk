status: todo
kind: bug
commit: fix(dotnet): retrieve counts lines like python
scope: dotnet/src/Gascoigne/Selection.cs, dotnet/tests/**, CHANGELOG.md

# dotnet Selection counts a phantom last line

`Selection.Of` splits the original on `\n`, so a text that ends in a newline gets one extra empty row. `spec/fixtures/raw.txt` gives 401 rows in .NET and 400 in Python (`str.splitlines`), so the cap note reads "... 201 more lines" where Python says "... 200 more lines". Line numbers past the end and range selections see the phantom row too. Make .NET count lines like Python: a trailing newline does not add a row.

Model: unchanged.

## Acceptance
- Regression test first, using `spec/fixtures/raw.txt`: the cap note says 200 more lines. Run it, see it fail with 201, then fix.
- A text without a trailing newline and an empty text behave as before (pin them in the same test table).
- `RetrieveOriginalTests` expectations that pinned 201 are updated to 200.
- `mise run check` passes.
