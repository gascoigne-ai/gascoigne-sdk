//! No LLM needed: optimize a noisy 400-line log, the way a tool result would be.
//!   cargo run --example logs
use gascoigne::{Attrs, Runtime};

fn noisy_log() -> String {
    let mut lines: Vec<String> = (0..400)
        .map(|i| {
            format!(
                "2026-10-13T12:{:02}:{:02}Z INFO worker-{} handled request id={i} took={}ms",
                i / 60,
                i % 60,
                i % 7,
                i % 90
            )
        })
        .collect();
    lines.insert(
        250,
        "2026-10-13T12:04:10Z ERROR db connection timeout after 30s (pool exhausted)".into(),
    );
    lines.join("\n")
}

fn main() {
    // 1. Start gascoigne.
    let rt = Runtime::new("rust-demo");

    // 2. Optimize the tool result.
    let res = rt.optimize_result(&noisy_log(), &Attrs::tool("search_logs"));

    if res.raw_id.is_empty() {
        println!("No optimization happened. Is the gascoigne CLI on PATH?");
        println!("Install: mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne");
        return;
    }
    println!("Tool result: {} tokens", res.raw_tokens);
    println!("Model reads: {} tokens\n", res.out_tokens);
    for line in res.text.lines().take(10) {
        println!("  {}", &line[..line.len().min(72)]);
    }
    let saved = 100 - res.out_tokens * 100 / res.raw_tokens;
    println!("\nSaved {saved}%. Original: gascoigne raw {}", res.raw_id);
}
