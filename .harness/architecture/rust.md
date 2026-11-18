# Rust
Crate `rust/` (`serde`, `serde_json`, `ureq`); `rust/native` adds the bundle.

| Zone | Files | Holds |
|---|---|---|
| core | `src/lib.rs` (types, `State`) | `Result`, `Attrs`, `Stats`, `Total`, `Run`, queries, breaker and warn-once state |
| adapters (in same file) | `src/lib.rs` | `healthy` (HTTP), `start_server` and `find_cli` (process); `Runtime` owns `Mutex<State>` |
| adapter (native) | `src/native.rs` | `Settings`, library lookup, `libloading` behind the `native` feature |
| adapter (bundle) | `native/src/lib.rs` | unpacks the bundled library (`flate2`, `sha2`), `runtime()` |
