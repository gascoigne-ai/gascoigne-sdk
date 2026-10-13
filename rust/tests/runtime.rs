use gascoigne::{Attrs, Runtime};
use std::io::{Read, Write};
use std::net::TcpListener;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};

/// Tiny HTTP stub: answers health, optimize (status configurable) and raw.
fn serve(proto: i64, optimize_status: u16) -> (String, Arc<AtomicUsize>, Arc<Mutex<String>>) {
    let l = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = l.local_addr().unwrap().to_string();
    let posts = Arc::new(AtomicUsize::new(0));
    let last = Arc::new(Mutex::new(String::new()));
    let (p, la) = (posts.clone(), last.clone());
    std::thread::spawn(move || {
        for s in l.incoming() {
            let mut s = s.unwrap();
            let req = read_request(&mut s);
            let (status, body) = if req.starts_with("GET /sdk/v1/health") {
                (200, format!(r#"{{"version":"t","proto":{proto}}}"#))
            } else if req.starts_with("POST /sdk/v1/optimize") {
                p.fetch_add(1, Ordering::SeqCst);
                *la.lock().unwrap() = req.clone();
                (
                    optimize_status,
                    r#"{"text":"short","raw_id":"abc","raw_tokens":100,"out_tokens":5}"#.into(),
                )
            } else {
                (200, "original".into())
            };
            let _ = write!(s, "HTTP/1.1 {status} X\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}", body.len());
        }
    });
    (addr, posts, last)
}

/// Reads headers plus `Content-Length` bytes of body.
fn read_request(s: &mut std::net::TcpStream) -> String {
    let mut data = Vec::new();
    let mut buf = [0u8; 4096];
    loop {
        let n = s.read(&mut buf).unwrap_or(0);
        data.extend_from_slice(&buf[..n]);
        let text = String::from_utf8_lossy(&data).to_string();
        let Some(i) = text.find("\r\n\r\n") else {
            if n == 0 {
                return text;
            }
            continue;
        };
        let want = text[..i]
            .to_lowercase()
            .split("content-length: ")
            .nth(1)
            .and_then(|r| r.split("\r\n").next()?.trim().parse::<usize>().ok())
            .unwrap_or(0);
        if data.len() >= i + 4 + want || n == 0 {
            return text;
        }
    }
}

fn clean() {
    for k in ["GASCOIGNE_SDK", "GASCOIGNE_SERVER", "GASCOIGNE_BIN"] {
        std::env::remove_var(k);
    }
}

// Tests share process env, so they run as one sequence.
#[test]
fn behaves() {
    clean();

    // missing CLI: pass through, no panic
    std::env::set_var("GASCOIGNE_SERVER_ADDR", "127.0.0.1:9");
    let saved = std::env::var_os("PATH");
    std::env::set_var("PATH", "");
    let rt = Runtime::new("t");
    assert_eq!(rt.optimize("hello", &Attrs::default()), "hello");
    assert!(rt.proxy_base_url("openai").is_none());
    assert_eq!(rt.raw("x"), "");
    std::env::set_var("PATH", saved.unwrap());

    // through the server
    let (addr, posts, last) = serve(1, 200);
    std::env::set_var("GASCOIGNE_SERVER_ADDR", &addr);
    let rt = Runtime::new("demo");
    let res = rt.optimize_result(&"long ".repeat(100), &Attrs::tool("grep"));
    assert_eq!(
        (res.text.as_str(), res.raw_id.as_str(), res.out_tokens),
        ("short", "abc", 5)
    );
    let req = last.lock().unwrap().clone();
    assert!(
        req.contains(r#""agent":"demo""#) && req.contains(r#""tool":"grep""#),
        "{req}"
    );
    assert_eq!(
        rt.stats(),
        gascoigne::Stats {
            raw_tokens: 100,
            out_tokens: 5
        }
    );
    assert!(rt.proxy_base_url("openai").unwrap().ends_with("/v1"));
    assert_eq!(rt.raw("abc"), "original");
    assert_eq!(posts.load(Ordering::SeqCst), 1);

    // failures: input back, breaker after five
    let (addr, posts, _) = serve(1, 500);
    std::env::set_var("GASCOIGNE_SERVER_ADDR", &addr);
    let rt = Runtime::new("t");
    for _ in 0..7 {
        assert_eq!(rt.optimize("text", &Attrs::default()), "text");
    }
    assert_eq!(posts.load(Ordering::SeqCst), 5);

    // kill switch
    std::env::set_var("GASCOIGNE_SDK", "off");
    assert_eq!(Runtime::new("t").optimize("x", &Attrs::default()), "x");
}
