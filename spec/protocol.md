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

### Runtime states

Every runtime is in exactly one state. Implement it as an enum and a transition table, not as flags.

| State | Meaning | Optimize calls |
|---|---|---|
| `off` | `GASCOIGNE_SERVER=off` or `GASCOIGNE_SDK=off` | bypass, no warning |
| `missing` | no CLI found and no server answering | bypass, one warning |
| `starting` | first probe running: health check, then `gascoigne server start` and polling | wait for the probe, then follow its result |
| `ready` | server answers with `proto` 1 (native mode: engine loaded) | sent to the server |
| `proto_mismatch` | server answers with another `proto` | bypass, one warning |
| `open_until` | breaker open until a time `T` | bypass until `T` |

`off` is read from the environment on every call, before any other state, and overrides all of them.
It is not stored: removing the variable returns the runtime to the stored state. The probe runs once
per runtime and its result is remembered: `missing` and `proto_mismatch` do not re-probe.
`open_until` is `ready` with a reopen time `T`, so the stored state is `ready` plus the fields below.

State kept besides the state: `failures` (consecutive optimize failures, starts at 0) and
`reopen_at` (time `T`, starts at 0, meaning no pause). The warning flag is once per runtime, not per
state: a second warning is never logged, whatever the cause.

| From | Event | To | Effect on `failures` and `reopen_at` |
|---|---|---|---|
| any | environment says off | `off` | none |
| `off` | environment no longer says off | stored state | none |
| start | first call, native mode | `ready` | none |
| start | first call, proxy mode | `starting` | none |
| `starting` | health answers `proto` 1 | `ready` | none |
| `starting` | health answers another `proto` | `proto_mismatch` | none; warn "server speaks proto N, SDK 1; running without optimization" |
| `starting` | health does not answer and no CLI (`$GASCOIGNE_BIN`, else `gascoigne` on `PATH`) | `missing` | none; warn `gascoigne-cli not found on PATH; running without optimization. Install: mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne` |
| `starting` | CLI found, `gascoigne server start` fails | `missing` | none; warn "could not start gascoigne server (error); running without optimization" |
| `starting` | CLI started, health polled every 100 ms for 3 s: answers `proto` 1 | `ready` | none |
| `starting` | polling ends without an answer | `missing` | none; warn "gascoigne server did not come up; running without optimization" |
| `ready` | optimize succeeds | `ready` | `failures` = 0 |
| `ready` | optimize fails (timeout, transport, status other than 200, bad answer), under 5 failures | `ready` | `failures` + 1; log at debug, return the input |
| `ready` | fifth consecutive failure | `open_until` | `failures` = 0; `reopen_at` = now + 60 s |
| `open_until` | now is `reopen_at` or later | `ready` | none; the next call tries again, and five more failures are needed to reopen |
| `ready`, native | `close` | `missing` | none; native calls bypass |

What each state allows:

| State | Optimize | Start server | Warn | Ledger reads (`totals`, `runs`) |
|---|---|---|---|---|
| `off` | no, returns input | no | no | empty |
| `missing` | no, returns input | no | already warned | empty |
| `starting` | waits for the probe | yes, once | yes | empty: reads never start the server |
| `ready` | yes | no | no | yes |
| `proto_mismatch` | no, returns input | no | already warned | empty |
| `open_until` | no, returns input | no | no | empty until `reopen_at` |

Every call in every state returns without raising. `proxy_base_url` returns no URL (none, null or
empty, as the language does) in every state but `ready`, so base URLs stay as they are in bypass.

Optimize calls have a timeout (default 5 s). The health probe has a timeout of 500 ms.

Rule 5 stays a rule:

- Never optimize text shorter than the server would touch anyway; the server returns it unchanged.

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

## Fixtures

Real responses of every route live in [`fixtures/`](fixtures/README.md), captured by
`scripts/capture_fixtures.sh`.
