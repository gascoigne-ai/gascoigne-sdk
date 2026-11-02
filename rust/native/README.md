# gascoigne-native

Adds the native variant to the `gascoigne` crate: the engine runs inside your process, with no
server and no CLI. Depend on it as a git dependency (a platform's library is too big for crates.io):

```rust
let runtime = gascoigne_native::runtime("my-agent", gascoigne::Settings::default());
```

The library for your platform is unpacked to the temporary directory on first use. See
`spec/native.md` in the repository.
