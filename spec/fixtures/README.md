# Fixtures

Real responses of every `/sdk/v1` route, captured from a `gascoigne` server.

- CLI version: 0.11.0 (8478f54)
- Proto: 1

| File | Route |
|---|---|
| `health.json` | `GET /sdk/v1/health` |
| `optimize_optimized.json` | `POST /sdk/v1/optimize`, text shrunk (has `raw_id`) |
| `optimize_skipped.json` | `POST /sdk/v1/optimize`, text below `min_tokens` (has `skipped`) |
| `raw.txt` | `GET /sdk/v1/raw/{id}` for the optimized call |
| `stats.json` | `GET /sdk/v1/stats` |
| `recent.json` | `GET /sdk/v1/recent` |

Regenerate with `scripts/capture_fixtures.sh [path-to-gascoigne]`. It runs the server with `HOME` and
`XDG_*` in a temp dir and a free `GASCOIGNE_SERVER_ADDR`, so your own config and ledger stay untouched.
Ids and timestamps change on every capture.
