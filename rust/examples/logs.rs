//! No LLM needed: optimize a noisy 400-line log, the way a tool result would be.
//!   cargo run --example logs
use gascoigne::{Attrs, Runtime};

fn noisy_log() -> String {
    let mut lines: Vec<String> = (0..400)
        .map(|i| {
            format!(
                "2026-10-13T12:{:02}:{:02}Z INFO worker-{} handled request id={i} status=200 took={}ms",
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
    let rt = Runtime::new("rust-demo"); // 1. start gascoigne
    let res = rt.optimize_result(&noisy_log(), &Attrs::tool("search_logs")); // 2. optimize the tool result

    if res.raw_id.is_empty() {
        println!("bypassed: is the gascoigne CLI on PATH?  mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne");
        return;
    }
    println!(
        "🐘 tool result · {} tokens\n🌘 model reads · {} tokens\n",
        res.raw_tokens, res.out_tokens
    );
    for line in res.text.lines().take(10) {
        println!("  │ {}", &line[..line.len().min(72)]);
    }
    let saved = 100 - res.out_tokens * 100 / res.raw_tokens;
    let bar = usize::try_from(saved * 30 / 100).unwrap_or(0);
    println!(
        "\n📉 savings \x1b[32m{}\x1b[31m{}\x1b[0m {saved}%  (original: gascoigne raw {})",
        "█".repeat(bar),
        "░".repeat(30 - bar),
        res.raw_id
    );
}
