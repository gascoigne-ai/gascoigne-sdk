# Native library (C ABI)

`native/` builds `libgascoigne` (`go build -buildmode=c-shared`), the gascoigne engine in-process.
It imports `gascoigne-cli/inproc`, so no server, no HTTP and no `gascoigne` binary are needed.

## Two variants per SDK: native and proxy

Every SDK offers both, chosen by the application:

| Mode | Transport | Needs | Choose it when |
|---|---|---|---|
| `native` | FFI into `libgascoigne` | the library, found as below | one process, no daemon, lowest latency |
| `proxy` | HTTP to `gascoigne server` (`protocol.md`) | the `gascoigne` CLI | the server is shared with agents, or the library cannot be loaded |

`GASCOIGNE_MODE=native|proxy` selects the default; the explicit argument to `init` wins. The SDK
itself stays thin: it carries no library.

## Finding the library

Native mode looks, in this order, and stops at the first hit:

1. `$GASCOIGNE_LIB`, a file. When set it is the only place looked at.
2. The system directories: `$GASCOIGNE_LIB_PATH` (a path list), the directory of `$GASCOIGNE_BIN`,
   then by platform
   - Linux: `~/.local/lib`, `/usr/local/lib`, `/usr/lib`, `/usr/lib64`, `/usr/lib/<arch>-linux-gnu`,
     `/opt/gascoigne/lib`
   - macOS: `~/.local/lib`, `/usr/local/lib`, `/opt/homebrew/lib`
   - Windows: `%LOCALAPPDATA%\gascoigne`, `%ProgramFiles%\gascoigne`

   for `libgascoigne.so`, `libgascoigne.dylib` or `gascoigne.dll`.
3. The optional per-platform dependency (below), unpacked to a temp directory. Skipped with
   `GASCOIGNE_UNPACK=off`.

When none yields a library, native mode is an error, not a silent bypass: the SDK raises at
construction (`init`, `build()`, the client constructor, `Runtime::native`) with a message naming
every place it looked. Proxy mode keeps the never-raise rules of `protocol.md`. A native runtime
never falls back to the server, because the application asked for no server.

## The per-platform dependency

Each language ships a native package per platform, so an application downloads one library
(about 9 MB gzip-compressed), not all five (about 48 MB). The package is optional; the SDK works
without it when the library is installed in a system directory.

| Language | Native package | Picked by |
|---|---|---|
| Python | `gascoigne-native` | pip, by wheel platform tag |
| TypeScript | `@gascoigne-ai/sdk-native` | npm optional dependencies (`os`, `cpu`) |
| Java | `ai.gascoigne:gascoigne-native` with a classifier `linux-amd64`, `darwin-arm64`, ... | you, e.g. os-maven-plugin |
| .NET | `Gascoigne.Native.<rid>` (`linux-x64`, `osx-arm64`, `win-x64`, ...) | you, with a `Condition` on the OS |
| Rust | `gascoigne-native` | Cargo, by `cfg(target_os, target_arch)` |
| Go | `gascoigne-sdk/native/embedded` | the engine is linked in, nothing to find |

The package holds `<os>-<arch>/<library file>.gz` (os `linux|darwin|windows`, arch
`amd64|arm64`), built by `scripts/package_native.py`. The SDK unpacks it into `$GASCOIGNE_LIB_DIR`
or the system temp directory, under `gascoigne-native-<sha256 of the library, first 16 hex>/`.
Unpacking is idempotent and safe between processes: the directory is created `0700`, the file is
written under a temporary name and renamed into place, and an existing file is reused only when its
sha256 matches. The SDK never deletes it (the library stays loaded, and Windows cannot delete a
loaded DLL).

## Config

The library owns configuration. It merges, later wins: built-in defaults, the user's file
(`$GASCOIGNE_CONFIG` or the per-user config dir; never written), the `config` YAML of the options,
then `set`, `only`, `disable`. SDKs pass their overrides as options and do no merging themselves.

## Functions

All strings are UTF-8, JSON unless noted. A returned `char*` is released with `gascoigne_free`.
On failure a function returns `NULL` (or 0) and stores a message in `*err` when `err` is not NULL.

| Function | In | Out |
|---|---|---|
| `int gascoigne_abi_version()` | | `3` |
| `uint64_t gascoigne_open(options, err)` | options JSON or `NULL` | handle, 0 on failure |
| `char* gascoigne_optimize(h, request, err)` | `{text, tool?, cmd?, url?, query?, session?, agent?, model?}` | `{text, raw_id?, raw_tokens, out_tokens, skipped?}` |
| `char* gascoigne_raw(h, id, err)` | raw id | original text |
| `char* gascoigne_config(options, err)` | options JSON | merged YAML, nothing started |
| `void gascoigne_close(h)` | | |
| `void gascoigne_free(s)` | | |

| `char* gascoigne_stats(h, query, err)` | `{by?, session?, agent?, model?, since?}`, `since` RFC 3339, `NULL` or `""` for none | `[{group, runs, optimized, failed, raw_tokens, out_tokens, saved, first?, last?}]` |
| `char* gascoigne_recent(h, query, err)` | `{session?, agent?, model?, since?, before?, limit?}` | `[{id, time, session?, agent?, model?, command?, route?, optimizers?, raw_tokens, out_tokens, duration_ns, raw_id?, outcome, reason?}]`, newest first |

Options: `{config?, set?[], only?[], disable?[], ignore_user_file?, timeout_ms?, ledger?}`.
Calls are thread-safe; a Go panic becomes an error, never a crash of the host.

## The ledger: file or memory

The engine records every run in a ledger. `ledger` picks where:

| Value | Meaning |
|---|---|
| `file` (default) | the sqlite file of the CLI configuration (`extensions.ledger.path`, `$GASCOIGNE_LEDGER`), shared with the CLI and its dashboard |
| `memory` | a private in-memory ledger: nothing touches the disk, it is gone at `gascoigne_close`, the stored originals are capped (64 MiB, oldest dropped first). It wins over `$GASCOIGNE_LEDGER` |

`gascoigne_stats` and `gascoigne_recent` read it: token counts only, no prices or dollars. `by` of a stats query is one of
`route` (default), `session`, `family`, `optimizer`, `command`, `outcome`, `agent`, `model`, `day`,
`week`, `month`; an unknown one is an error. `recent` returns at most `limit` runs (default 50, at
most 1000) with a run `id` smaller than `before`. A run recorded for instruction text has no `raw_id`.
An empty ledger gives `[]`.

## Version history

- `1`: `open`, `optimize`, `raw`, `config`, `close`, `free`.
- `2` (0.10.0): added `stats`, `recent`, `costs` and the options `ledger` and `pricing`.
- `3`: drops `costs` and `pricing`; the SDK counts tokens only. Keeps `stats`, `recent` and `ledger`. Functions of 1 behave
  as before; an SDK built for 2 refuses a library of 1, as the other way round.
