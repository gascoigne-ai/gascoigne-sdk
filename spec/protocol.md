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
| `GET /sdk/v1/costs` | `?session=&agent=&model=&since=` | `{billing, first_read_usd, in_context_usd, rereads, savings: [...], unpriced?}` |

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

## Ledger reads (`stats`, `recent`, `costs`)

Every SDK exposes them as `totals`, `runs` and `costs` (the language's casing), in proxy mode through
the routes above, in native mode through `gascoigne_stats`, `gascoigne_recent` and
`gascoigne_costs` (`native.md`). Proxy mode reads the user's own ledger, the one the dashboard
shows; native mode reads the engine's ledger (`ledger: memory` makes it private to the process).
The answers are the same JSON in both.

- `since` is an RFC 3339 time; a bad one, an unknown `by`, or a bad number is a 400.
- `costs` is an estimate from list prices or the prices the user set with `gascoigne pricing`, not a
  bill. `billing` is `api`, `subscription` (every agent is on a plan: no dollars) or `mixed` (agents on
  a plan, named in `subscription_agents`, are left out of the dollars). The server decides per agent from
  how the agent is signed in, unless the user set it. `source` per model: `built-in`, `static`, `json`,
  `api` or `script`.
- **Reads never raise and never count toward the breaker.** On any failure (bypass, server down,
  timeout, bad answer, bad query) they return an empty list, or an empty `costs` (`billing` is `""`),
  and log at debug. Go returns the empty value with an error instead, as Go does.
- They do not start the server: with the SDK off or the CLI missing they are empty.
