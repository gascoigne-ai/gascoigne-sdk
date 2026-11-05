# SDK protocol (proto 1)

Every SDK talks to the local gascoigne server (`gascoigne-cli`, `cmd/gascoigne/sdk.go`).
Address: `$GASCOIGNE_SERVER_ADDR` or `127.0.0.1:7878`.

| Route | Request | Response |
|---|---|---|
| `GET /sdk/v1/health` | | `{version, proto, proxy}` |
| `POST /sdk/v1/optimize` | `{text, tool?, cmd?, url?, query?, session?, agent?, model?}` | `{text, raw_id?, raw_tokens, out_tokens, skipped?}` |
| `GET /sdk/v1/raw/{id}` | | original text |
| `GET /sdk/v1/stats` | `?by=&session=&agent=&model=&since=` (`since` RFC 3339) | `[{group, runs, optimized, failed, raw_tokens, out_tokens, saved, first?, last?}]` |
| `GET /sdk/v1/recent` | `?session=&agent=&model=&since=&before=&limit=` | `[{id, time, session?, agent?, model?, command?, route?, optimizers?, raw_tokens, out_tokens, duration_ns, raw_id?, outcome, reason?}]`, newest first |

## Behavior every SDK implements

1. **Find the CLI**: `$GASCOIGNE_BIN`, else `gascoigne` on `PATH`. Missing and no server answering ->
   log one warning (`gascoigne-cli not found on PATH; running without optimization. Install: mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne`)
   and **bypass**: every call returns its input unchanged, base URLs stay as they are. Never raise.
2. **Start the server** when `/sdk/v1/health` does not answer: run `gascoigne server start`, poll health for up to 3 s.
   `GASCOIGNE_SERVER=off` or `GASCOIGNE_SDK=off` -> bypass without warning.
3. `proto` other than 1 -> warn once, bypass.
4. Every optimize call has a timeout (default 5 s). Any error -> return the input, log at debug.
   Five consecutive failures open a breaker: bypass for 60 s, then try again.
5. Never optimize text shorter than the server would touch anyway; the server returns it unchanged.

## Ledger reads (`stats`, `recent`)

Every SDK exposes them as `totals` and `runs` (the language's casing), in proxy mode through the
routes above, in native mode through `gascoigne_stats` and `gascoigne_recent` (`native.md`). They are
token counts: the SDK has no prices and shows no dollars. Proxy mode reads the user's own ledger,
the one the dashboard shows; native mode reads the engine's ledger (`ledger: memory` makes it
private to the process). The answers are the same JSON in both.

- `since` is an RFC 3339 time; a bad one, an unknown `by`, or a bad number is a 400.
- `limit` above 1000 means 1000.
- **Reads never raise and never count toward the breaker.** On any failure (bypass, server down,
  timeout, bad answer, bad query) they return an empty list and log at debug. Go returns the empty
  value with an error instead, as Go does.
- They do not start the server: with the SDK off or the CLI missing they are empty.
