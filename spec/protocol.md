# SDK protocol (proto 1)

Every SDK talks to the local gascoigne server (`gascoigne-cli`, `cmd/gascoigne/sdk.go`).
Address: `$GASCOIGNE_SERVER_ADDR` or `127.0.0.1:7878`.

| Route | Request | Response |
|---|---|---|
| `GET /sdk/v1/health` | | `{version, proto, proxy}` |
| `POST /sdk/v1/optimize` | `{text, tool?, cmd?, url?, query?, session?, agent?, model?}` | `{text, raw_id?, raw_tokens, out_tokens, skipped?}` |
| `GET /sdk/v1/raw/{id}` | | original text |

## Behavior every SDK implements

1. **Find the CLI**: `$GASCOIGNE_BIN`, else `gascoigne` on `PATH`. Missing and no server answering →
   log one warning (`gascoigne-cli not found on PATH; running without optimization. Install: mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne`)
   and **bypass**: every call returns its input unchanged, base URLs stay as they are. Never raise.
2. **Start the server** when `/sdk/v1/health` does not answer: run `gascoigne server start`, poll health for up to 3 s.
   `GASCOIGNE_SERVER=off` or `GASCOIGNE_SDK=off` → bypass without warning.
3. `proto` other than 1 → warn once, bypass.
4. Every optimize call has a timeout (default 5 s). Any error → return the input, log at debug.
   Five consecutive failures open a breaker: bypass for 60 s, then try again.
5. Never optimize text shorter than the server would touch anyway; the server returns it unchanged.
