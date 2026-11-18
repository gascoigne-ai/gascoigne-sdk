//! Every real response in `spec/fixtures` decodes into the typed wire models.
use gascoigne::{Health, Outcome, Result as Answer, Route, Run, Total};

fn fixture(name: &str) -> String {
    let path = format!("{}/../spec/fixtures/{name}", env!("CARGO_MANIFEST_DIR"));
    std::fs::read_to_string(&path).unwrap_or_else(|error| panic!("{path}: {error}"))
}

#[test]
fn health() {
    let health: Health = serde_json::from_str(&fixture("health.json")).unwrap();
    assert_eq!((health.proto, health.proxy), (1, true));
    assert!(health.version.starts_with("0.11.0"));
}

#[test]
fn optimize_optimized() {
    let r: Answer = serde_json::from_str(&fixture("optimize_optimized.json")).unwrap();
    assert_eq!(
        (r.raw_id.as_str(), r.raw_tokens, r.out_tokens),
        ("a4e762ac", 9200, 34)
    );
    assert!(r.skipped.is_empty());
}

#[test]
fn optimize_skipped() {
    let r: Answer = serde_json::from_str(&fixture("optimize_skipped.json")).unwrap();
    assert_eq!((r.text.as_str(), r.raw_id.as_str()), ("ok", ""));
    assert_eq!(r.skipped, "1 tokens < min_tokens 200");
}

#[test]
fn raw_is_plain_text() {
    assert!(fixture("raw.txt").starts_with("2026-01-01T00:00:00Z INFO worker"));
}

#[test]
fn stats() {
    let totals: Vec<Total> = serde_json::from_str(&fixture("stats.json")).unwrap();
    assert_eq!(totals.len(), 2);
    assert_eq!(
        (totals[0].group.as_str(), totals[0].saved),
        ("default", 9166)
    );
    assert_eq!(totals[1].group, "-");
    assert!(totals[1].first.starts_with("2026-11-18"));
}

#[test]
fn recent_keeps_order_and_optionals() {
    let runs: Vec<Run> = serde_json::from_str(&fixture("recent.json")).unwrap();
    assert_eq!(runs.iter().map(|run| run.id).collect::<Vec<_>>(), [2, 1]);
    assert_eq!(runs[0].outcome, Outcome::Bypassed);
    assert_eq!(runs[0].route, None);
    assert!(runs[0].optimizers.is_empty());
    assert_eq!(runs[0].reason, "1 tokens < min_tokens 200");
    assert_eq!(runs[1].outcome, Outcome::Optimized);
    assert_eq!(runs[1].route, Some(Route::Default));
    assert_eq!(runs[1].optimizers.len(), 28);
    assert_eq!(runs[1].duration_ns, 5_000_000);
}

#[test]
fn unknown_values_are_kept() {
    let body = r#"{"id":1,"time":"t","raw_tokens":1,"out_tokens":1,"duration_ns":1,
        "outcome":"shrugged","route":"custom"}"#;
    let run: Run = serde_json::from_str(body).unwrap();
    assert_eq!(run.outcome, Outcome::Other("shrugged".into()));
    assert_eq!(run.route, Some(Route::Other("custom".into())));
}

#[test]
fn required_fields_are_required() {
    assert!(serde_json::from_str::<Answer>(r#"{"text":"x","out_tokens":1}"#).is_err());
    assert!(serde_json::from_str::<Total>(r#"{"group":"g"}"#).is_err());
    assert!(serde_json::from_str::<Run>(r#"{"id":1}"#).is_err());
    assert!(serde_json::from_str::<Health>(r#"{"version":"v"}"#).is_err());
}
