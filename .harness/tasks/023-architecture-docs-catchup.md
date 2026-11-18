status: todo
kind: docs
commit: docs(harness): architecture maps match the code
scope: .harness/architecture.md, .harness/architecture/**, .harness/code-style.md

# Architecture docs catch up with the code

Several tasks changed structure while their scope excluded the docs. Update the maps from the code as it is now, and change nothing else.

- `.harness/architecture.md`: rewrite "Known mixing" for Python (runtime.py is split into `state.py`, `http.py`, `process.py`; name what still mixes in `runtime.py`, if anything). Mention `scripts/style.py --params`, which `make check` now runs over the tracked sources. List the TypeScript wire decoders.
- `.harness/architecture/python.md`: models `Health`, `Outcome`, `Route`; wire answers parsed once in `models.py`.
- `.harness/architecture/typescript.md`: `Health`, the `Outcome` and `Route` unions and the `decode*` functions in the core zone.
- `.harness/architecture/rust.md`: `Health`, `Outcome`, `Route` in the core zone; the `get` and `percent_encode` helpers around the HTTP client.
- `.harness/architecture/java.md`: package-private `State`, `Event`, `Machine`; `Gascoigne.java` delegates its runtime state to `Machine`.
- `.harness/code-style.md`: one line that parameter names are checked by `scripts/style.py` (no one-letter names, exemptions as in the common rules).

Read each file listed from the source before writing: every claim in a map is checked against the code.

Model: unchanged.

## Acceptance
- Every type and file named above appears in its map and exists in the code.
- No home paths, lines at most 100 columns.
- `make check` passes.
