use gascoigne::{Costs, Run, RunsQuery, Runtime, Total, TotalsQuery};
use std::io::{Read, Write};
use std::net::TcpListener;
use std::sync::{Arc, Mutex};

/// The tests set process-wide environment variables: one at a time.
static ENV: Mutex<()> = Mutex::new(());

const TOTALS: &str = r#"[{"group":"sdk","runs":2,"optimized":2,"failed":0,
"raw_tokens":100,"out_tokens":40,"saved":60}]"#;
const RUNS: &str = r#"[{"id":7,"time":"2026-11-01T10:00:00Z","session":"s1",
"raw_tokens":100,"out_tokens":10,"raw_id":"abc","outcome":"optimized","optimizers":["log"]}]"#;
const COSTS: &str = r#"{"billing":"api","first_read_usd":0.5,"in_context_usd":1.5,
"rereads":110,"savings":[{"model":"m","source":"static","tokenizer":"o200k","tokens":10,
"model_tokens":10,"first_read_usd":0.5,"in_context_usd":1.5}]}"#;

/// Tiny HTTP stub for health and the ledger routes; `status` answers the ledger ones. It records
/// the request targets.
fn serve(status: u16) -> (String, Arc<Mutex<Vec<String>>>) {
    let l = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = l.local_addr().unwrap().to_string();
    let seen = Arc::new(Mutex::new(Vec::new()));
    let log = seen.clone();
    std::thread::spawn(move || {
        for s in l.incoming() {
            let mut s = s.unwrap();
            let mut buf = [0u8; 4096];
            let n = s.read(&mut buf).unwrap_or(0);
            let req = String::from_utf8_lossy(&buf[..n]).to_string();
            let target = req.split_whitespace().nth(1).unwrap_or("").to_string();
            let (code, body) = if target.starts_with("/sdk/v1/health") {
                (200, r#"{"version":"t","proto":1}"#.to_string())
            } else {
                log.lock().unwrap().push(target.clone());
                let body = if status != 200 {
                    "boom"
                } else if target.starts_with("/sdk/v1/stats") {
                    TOTALS
                } else if target.starts_with("/sdk/v1/recent") {
                    RUNS
                } else {
                    COSTS
                };
                (status, body.to_string())
            };
            let head = format!(
                "HTTP/1.1 {code} X\r\nContent-Type: application/json\r\n\
                 Content-Length: {}\r\nConnection: close\r\n\r\n",
                body.len()
            );
            let _ = write!(s, "{head}{body}");
        }
    });
    (addr, seen)
}

fn same_query(expected: &str, actual: &str) {
    let split = |t: &str| {
        let (path, query) = t.split_once('?').unwrap_or((t, ""));
        let mut pairs: Vec<String> = query.split('&').map(str::to_string).collect();
        pairs.sort();
        (path.to_string(), pairs)
    };
    assert_eq!(split(expected), split(actual));
}

#[test]
fn reads_through_the_server() {
    let _env = ENV
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    let (addr, seen) = serve(200);
    std::env::set_var("GASCOIGNE_SERVER_ADDR", &addr);
    std::env::remove_var("GASCOIGNE_SDK");
    let rt = Runtime::new("t");
    let totals = rt.totals(&TotalsQuery {
        by: "agent".into(),
        session: "s 1".into(),
        since: "2026-11-01T00:00:00Z".into(),
        ..TotalsQuery::default()
    });
    assert_eq!(
        totals,
        vec![Total {
            group: "sdk".into(),
            runs: 2,
            optimized: 2,
            raw_tokens: 100,
            out_tokens: 40,
            saved: 60,
            ..Total::default()
        }]
    );
    let runs: Vec<Run> = rt.runs(&RunsQuery {
        session: "s1".into(),
        limit: 5,
        before: 9,
        ..RunsQuery::default()
    });
    assert_eq!((runs[0].id, runs[0].raw_id.as_str()), (7, "abc"));
    assert_eq!(runs[0].optimizers, vec!["log".to_string()]);
    let costs: Costs = rt.costs(&TotalsQuery::default());
    assert_eq!(costs.billing, "api");
    assert!((costs.in_context_usd - 1.5).abs() < f64::EPSILON);
    assert_eq!(costs.savings[0].source, "static");
    let seen = seen.lock().unwrap();
    same_query(
        "/sdk/v1/stats?by=agent&session=s+1&since=2026-11-01T00%3A00%3A00Z",
        &seen[0],
    );
    same_query("/sdk/v1/recent?before=9&limit=5&session=s1", &seen[1]);
}

#[test]
fn failures_are_empty_and_keep_the_breaker_closed() {
    let _env = ENV
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    let (addr, _) = serve(500);
    std::env::set_var("GASCOIGNE_SERVER_ADDR", &addr);
    std::env::remove_var("GASCOIGNE_SDK");
    let rt = Runtime::new("t");
    for _ in 0..10 {
        assert!(rt.totals(&TotalsQuery::default()).is_empty());
    }
    assert!(rt.runs(&RunsQuery::default()).is_empty());
    assert_eq!(rt.costs(&TotalsQuery::default()).billing, "");
    assert!(rt.ready());
}

#[test]
fn bypass_is_empty() {
    let _env = ENV
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    std::env::set_var("GASCOIGNE_SDK", "off");
    let rt = Runtime::new("t");
    assert!(rt.totals(&TotalsQuery::default()).is_empty());
    assert!(rt.costs(&TotalsQuery::default()).savings.is_empty());
    std::env::remove_var("GASCOIGNE_SDK");
}
