# Native library
Go module `native/`; implements `spec/native.md`, loaded by every SDK's native adapter.

| Zone | Files | Holds |
|---|---|---|
| core | `core/core.go` | handle table, options and request/response types, `ABIVersion`, JSON in and out; no cgo |
| adapter (C ABI) | `main.go` | cgo exports `gascoigne_open`, `_optimize`, `_raw`, `_stats`, `_recent`, `_close`, `_free` |
| adapter (Go) | `embedded/embedded.go` | `gascoigne.Backend` over the in-process engine, for Go apps |
| examples | `examples/` | C smoke test, plain Go |
