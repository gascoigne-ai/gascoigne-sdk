# Go
Module `go/gascoigne`; standard library only.

| Zone | Files | Holds |
|---|---|---|
| core | `gascoigne.go` (types) | `Result`, `Attrs`, `Request`, `Options` |
| core (port) | `gascoigne.go` `Backend`, `ledger.go` `LedgerBackend` | seam for an in-process engine; the native module implements it |
| core | `ledger.go` | `Total`, `Run`, queries |
| core + adapters (mixed) | `gascoigne.go` `Runtime` | availability, breaker, warn-once, token counts, HTTP client, `startServer` spawn |
| helper | `tool.go` | `WrapTool`, `WrapFunc` for langchaingo |

The native-backed `Backend` lives in `native/embedded`; see `native.md`.
