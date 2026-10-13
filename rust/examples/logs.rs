//! Quick demo, no LLM: optimize a noisy 400-line log and show what the model would read.
//!   cargo run --example logs
use gascoigne::{Attrs, Runtime};

fn main() {
    let mut lines: Vec<String> = (0..400)
        .map(|i| format!("2026-10-13T12:{:02}:{:02}Z INFO worker-{} handled request id={i} status=200 took={}ms", i / 60, i % 60, i % 7, i % 90))
        .collect();
    lines.insert(
        250,
        "2026-10-13T12:04:10Z ERROR db connection timeout after 30s (pool exhausted)".into(),
    );
    let log = lines.join("\n");

    let rt = Runtime::new("rust-demo");
    let res = rt.optimize_result(&log, &Attrs::tool("search_logs"));
    if res.raw_id.is_empty() {
        println!("bypassed: is the gascoigne CLI on PATH?  mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne");
        return;
    }
    println!("🌘 gascoigne · agents read less, nothing gets lost\n");
    println!(
        "🐘 tool result · {} tokens\n🌘 model reads · {} tokens\n",
        res.raw_tokens, res.out_tokens
    );
    for l in res.text.lines().take(10) {
        println!("  │ {}", &l[..l.len().min(72)]);
    }
    let saved = 1.0 - res.out_tokens as f64 / res.raw_tokens as f64;
    let n = (saved * 30.0) as usize;
    println!(
        "\n📉 savings \x1b[32m{}\x1b[31m{}\x1b[0m {:.0}%  (original: gascoigne raw {})",
        "█".repeat(n),
        "░".repeat(30 - n),
        saved * 100.0,
        res.raw_id
    );
}
