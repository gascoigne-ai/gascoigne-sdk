status: todo
kind: chore
commit: refactor(python): runtime splits into state, HTTP and process
scope: python/gascoigne/src/gascoigne/**, python/gascoigne/tests/**, .harness/architecture/**
depends_on: 005-python-runtime-state, 002-architecture-index

# Split python runtime.py

`runtime.py` (409 lines) mixes HTTP, process spawn, breaker, lock and stats. Core: state, stats, lock. Adapters: HTTP client and server process. The test fake shows the HTTP port is real.

Model: unchanged.

## Acceptance
- Tests unchanged and green.
- Architecture doc updated in the same commit.
- `mise run check` passes.
