//! Embed gascoigne token optimization in agent frameworks.
//!
//! Every call is safe: when the gascoigne CLI is missing or the server misbehaves, inputs come back
//! unchanged and no error reaches the caller.

use std::process::{Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

const PROTO: i64 = 1;
const DEFAULT_ADDR: &str = "127.0.0.1:7878";
const INSTALL_HINT: &str = "mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne";
const BREAKER_FAILURES: u32 = 5;
const BREAKER_PAUSE: Duration = Duration::from_secs(60);

/// One optimize call: `text` is what the model should read.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct Result {
    pub text: String,
    pub raw_id: String,
    pub raw_tokens: u64,
    pub out_tokens: u64,
    pub skipped: String,
}

/// Where the text came from; empty fields are left out.
#[derive(Debug, Clone, Default)]
pub struct Attrs {
    pub tool: String,
    pub cmd: String,
    pub url: String,
    pub query: String,
    pub model: String,
}

impl Attrs {
    pub fn tool(name: &str) -> Self {
        Attrs {
            tool: name.into(),
            ..Default::default()
        }
    }
}

#[derive(Default)]
struct State {
    ready: Option<bool>,
    failures: u32,
    paused_until: Option<Instant>,
    warned: bool,
    raw_tokens: u64,
    out_tokens: u64,
}

/// Finds the CLI, makes sure its server runs, and optimizes text through it.
pub struct Runtime {
    agent: String,
    timeout: Duration,
    state: Mutex<State>,
}

fn env(name: &str) -> String {
    std::env::var(name).unwrap_or_default()
}

fn find_on_path(name: &str) -> Option<std::path::PathBuf> {
    std::env::split_paths(&std::env::var_os("PATH")?)
        .map(|d| d.join(name))
        .find(|p| p.is_file())
}

impl Runtime {
    pub fn new(agent: &str) -> Self {
        Runtime {
            agent: agent.into(),
            timeout: Duration::from_secs(5),
            state: Mutex::new(State::default()),
        }
    }

    fn base_url(&self) -> String {
        let a = env("GASCOIGNE_SERVER_ADDR");
        format!("http://{}", if a.is_empty() { DEFAULT_ADDR } else { &a })
    }

    fn warn(&self, st: &mut State, msg: &str) {
        if !st.warned {
            st.warned = true;
            eprintln!("[gascoigne] {msg}");
        }
    }

    fn healthy(&self, st: &mut State) -> bool {
        let url = format!("{}/sdk/v1/health", self.base_url());
        let Ok(resp) = ureq::get(&url).timeout(Duration::from_millis(500)).call() else {
            return false;
        };
        let proto = resp
            .into_json::<serde_json::Value>()
            .ok()
            .and_then(|v| v["proto"].as_i64());
        if proto != Some(PROTO) {
            self.warn(
                st,
                &format!(
                    "server speaks proto {proto:?}, SDK {PROTO}; running without optimization"
                ),
            );
            return false;
        }
        true
    }

    fn start_server(&self, st: &mut State) -> bool {
        let exe = match env("GASCOIGNE_BIN") {
            e if !e.is_empty() => Some(e.into()),
            _ => find_on_path("gascoigne"),
        };
        let Some(exe) = exe else {
            self.warn(st, &format!("gascoigne-cli not found on PATH; running without optimization. Install: {INSTALL_HINT}"));
            return false;
        };
        let status = Command::new(&exe)
            .args(["server", "start"])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
        if let Err(e) = status {
            self.warn(
                st,
                &format!("could not start gascoigne server ({e}); running without optimization"),
            );
            return false;
        }
        let end = Instant::now() + Duration::from_secs(3);
        while Instant::now() < end {
            if self.healthy(st) {
                return true;
            }
            std::thread::sleep(Duration::from_millis(100));
        }
        self.warn(
            st,
            "gascoigne server did not come up; running without optimization",
        );
        false
    }

    /// True when optimize calls will be tried. Probes once, then remembers.
    pub fn ready(&self) -> bool {
        if env("GASCOIGNE_SDK") == "off" || env("GASCOIGNE_SERVER") == "off" {
            return false;
        }
        let mut st = self.state.lock().unwrap();
        if st.ready.is_none() {
            let ok = self.healthy(&mut st) || self.start_server(&mut st);
            st.ready = Some(ok);
        }
        st.ready == Some(true) && st.paused_until.is_none_or(|t| Instant::now() >= t)
    }

    /// Optimize `text`; on any problem the result carries the input unchanged.
    pub fn optimize_result(&self, text: &str, attrs: &Attrs) -> Result {
        let same = Result {
            text: text.into(),
            ..Default::default()
        };
        if text.is_empty() || !self.ready() {
            return same;
        }
        let mut body = serde_json::json!({ "text": text });
        for (k, v) in [
            ("agent", self.agent.as_str()),
            ("tool", &attrs.tool),
            ("cmd", &attrs.cmd),
            ("url", &attrs.url),
            ("query", &attrs.query),
            ("model", &attrs.model),
        ] {
            if !v.is_empty() {
                body[k] = v.into();
            }
        }
        let url = format!("{}/sdk/v1/optimize", self.base_url());
        let reply = ureq::post(&url)
            .timeout(self.timeout)
            .send_json(body)
            .ok()
            .and_then(|r| r.into_json::<serde_json::Value>().ok())
            .filter(|v| v["text"].is_string());
        let mut st = self.state.lock().unwrap();
        let Some(v) = reply else {
            st.failures += 1;
            if st.failures >= BREAKER_FAILURES {
                st.failures = 0;
                st.paused_until = Some(Instant::now() + BREAKER_PAUSE);
            }
            return same;
        };
        st.failures = 0;
        let out = Result {
            text: v["text"].as_str().unwrap_or_default().into(),
            raw_id: v["raw_id"].as_str().unwrap_or_default().into(),
            raw_tokens: v["raw_tokens"].as_u64().unwrap_or(0),
            out_tokens: v["out_tokens"].as_u64().unwrap_or(0),
            skipped: v["skipped"].as_str().unwrap_or_default().into(),
        };
        st.raw_tokens += out.raw_tokens;
        st.out_tokens += if out.out_tokens > 0 {
            out.out_tokens
        } else {
            out.raw_tokens
        };
        out
    }

    pub fn optimize(&self, text: &str, attrs: &Attrs) -> String {
        self.optimize_result(text, attrs).text
    }

    /// The original behind an optimized result; empty when unavailable.
    pub fn raw(&self, raw_id: &str) -> String {
        if !self.ready() {
            return String::new();
        }
        let url = format!("{}/sdk/v1/raw/{raw_id}", self.base_url());
        ureq::get(&url)
            .timeout(self.timeout)
            .call()
            .ok()
            .and_then(|r| r.into_string().ok())
            .unwrap_or_default()
    }

    /// Base URL that routes an LLM client through the gascoigne proxy, or `None` in bypass.
    /// `api` is "openai" (`/v1`), "anthropic" or "gemini".
    pub fn proxy_base_url(&self, api: &str) -> Option<String> {
        if !self.ready() {
            return None;
        }
        let base = self.base_url();
        Some(if api == "openai" {
            format!("{base}/v1")
        } else {
            base
        })
    }

    /// Tokens (estimated) before and after, summed over this runtime's calls.
    pub fn stats(&self) -> (u64, u64) {
        let st = self.state.lock().unwrap();
        (st.raw_tokens, st.out_tokens)
    }

    /// Wrap a tool function so the string it returns is optimized.
    pub fn wrap_tool<A, F>(&self, name: &str, f: F) -> impl Fn(A) -> String + '_
    where
        F: Fn(A) -> String + 'static,
    {
        let name = name.to_string();
        move |a| self.optimize(&f(a), &Attrs::tool(&name))
    }
}
