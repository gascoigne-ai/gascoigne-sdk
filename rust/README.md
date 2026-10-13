# gascoigne (Rust)

Optimize tool results before your model reads them. Without the `gascoigne` CLI on `PATH` it logs one warning and returns inputs unchanged.

```rust
let rt = gascoigne::Runtime::new("my-agent");
let short = rt.optimize(&tool_output, &gascoigne::Attrs::tool("grep"));
```

