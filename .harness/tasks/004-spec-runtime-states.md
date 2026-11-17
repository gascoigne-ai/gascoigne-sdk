status: todo
kind: docs
commit: docs(spec): runtime states and transitions for every SDK
scope: spec/protocol.md

# Runtime state table in the spec

Replace the prose of rules 1 to 4 with a state enum and a transition table every SDK implements.

## Model
States: off, missing, starting, ready, proto_mismatch, open_until. The table says each state's transitions, the failure counter and the reopen time, and what each state allows.

## Acceptance
- The table covers every case of rules 1 to 4.
- `mise run check` passes.
