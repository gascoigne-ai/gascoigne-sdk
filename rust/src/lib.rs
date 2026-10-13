//! Embed gascoigne token optimization in agent frameworks.
//!
//! Every call is safe: when the gascoigne CLI is missing or the server misbehaves, inputs come back
//! unchanged and no error reaches the caller.

use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::{Mutex, MutexGuard, PoisonError};
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};

const PROTO: u32 = 1;
const DEFAULT_ADDR: &str = "127.0.0.1:7878";
const INSTALL_HINT: &str = "mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne";
const BREAKER_FAILURES: u32 = 5;
const BREAKER_PAUSE: Duration = Duration::from_secs(60);

/// One optimize call: `text` is what the model should read.
#[derive(Debug, Clone, Default, PartialEq, Eq, Deserialize)]
#[serde(default)]
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
    #[must_use]
    pub fn tool(name: &str) -> Self {
        Attrs {
            tool: name.into(),
            ..Default::default()
        }
    }
}

/// Tokens (estimated) before and after, summed over a runtime's calls.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Stats {
    pub raw_tokens: u64,
    pub out_tokens: u64,
}

/// Body of `POST /sdk/v1/optimize`.
#[derive(Serialize)]
struct OptimizeRequest<'a> {
    text: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    agent: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    tool: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    cmd: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    url: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    query: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    model: &'a str,
}

/// Response of `GET /sdk/v1/health`.
#[derive(Deserialize)]
struct Health {
    proto: u32,
}

#[derive(Default)]
struct State {
    available: Option<bool>,
    failures: u32,
    paused_until: Option<Instant>,
    warned: bool,
    stats: Stats,
}

impl State {
    fn warn(&mut self, msg: &str) {
        if !self.warned {
            self.warned = true;
            eprintln!("[gascoigne] {msg}");
        }
    }
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

fn base_url() -> String {
    let addr = env("GASCOIGNE_SERVER_ADDR");
    format!(
        "http://{}",
        if addr.is_empty() { DEFAULT_ADDR } else { &addr }
    )
}

fn find_cli() -> Option<PathBuf> {
    let bin = env("GASCOIGNE_BIN");
    if !bin.is_empty() {
        return Some(bin.into());
    }
    std::env::split_paths(&std::env::var_os("PATH")?)
        .map(|dir| dir.join("gascoigne"))
        .find(|path| path.is_file())
}

fn healthy(state: &mut State) -> bool {
    let url = format!("{}/sdk/v1/health", base_url());
    let Ok(response) = ureq::get(&url).timeout(Duration::from_millis(500)).call() else {
        return false;
    };
    let Ok(health) = response.into_json::<Health>() else {
        return false;
    };
    if health.proto != PROTO {
        state.warn(&format!(
            "server speaks proto {}, SDK {PROTO}; running without optimization",
            health.proto
        ));
    }
    health.proto == PROTO
}

fn start_server(state: &mut State) -> bool {
    let Some(exe) = find_cli() else {
        state.warn(&format!(
            "gascoigne-cli not found on PATH; running without optimization. Install: {INSTALL_HINT}"
        ));
        return false;
    };
    let started = Command::new(&exe)
        .args(["server", "start"])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status();
    if let Err(e) = started {
        state.warn(&format!(
            "could not start gascoigne server ({e}); running without optimization"
        ));
        return false;
    }
    let deadline = Instant::now() + Duration::from_secs(3);
    while Instant::now() < deadline {
        if healthy(state) {
            return true;
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    state.warn("gascoigne server did not come up; running without optimization");
    false
}

impl Runtime {
    #[must_use]
    pub fn new(agent: &str) -> Self {
        Runtime {
            agent: agent.into(),
            timeout: Duration::from_secs(5),
            state: Mutex::default(),
        }
    }

    /// A poisoned lock only means another thread panicked; the counters inside stay usable.
    fn state(&self) -> MutexGuard<'_, State> {
        self.state.lock().unwrap_or_else(PoisonError::into_inner)
    }

    /// True when optimize calls will be tried. Probes once, then remembers.
    pub fn ready(&self) -> bool {
        if env("GASCOIGNE_SDK") == "off" || env("GASCOIGNE_SERVER") == "off" {
            return false;
        }
        let mut state = self.state();
        if state.available.is_none() {
            let available = healthy(&mut state) || start_server(&mut state);
            state.available = Some(available);
        }
        let available = state.available == Some(true);
        available
            && state
                .paused_until
                .is_none_or(|until| Instant::now() >= until)
    }

    fn record_failure(&self) {
        let mut state = self.state();
        state.failures += 1;
        if state.failures >= BREAKER_FAILURES {
            state.failures = 0;
            state.paused_until = Some(Instant::now() + BREAKER_PAUSE);
        }
    }

    fn post(&self, request: &OptimizeRequest) -> Option<Result> {
        let url = format!("{}/sdk/v1/optimize", base_url());
        let response = ureq::post(&url)
            .timeout(self.timeout)
            .send_json(request)
            .ok()?;
        response
            .into_json::<Result>()
            .ok()
            .filter(|r| !r.text.is_empty())
    }

    /// Optimize `text`; on any problem the result carries the input unchanged.
    pub fn optimize_result(&self, text: &str, attrs: &Attrs) -> Result {
        let unchanged = Result {
            text: text.into(),
            ..Default::default()
        };
        if text.is_empty() || !self.ready() {
            return unchanged;
        }
        let request = OptimizeRequest {
            text,
            agent: &self.agent,
            tool: &attrs.tool,
            cmd: &attrs.cmd,
            url: &attrs.url,
            query: &attrs.query,
            model: &attrs.model,
        };
        let Some(result) = self.post(&request) else {
            self.record_failure();
            return unchanged;
        };
        let mut state = self.state();
        state.failures = 0;
        state.stats.raw_tokens += result.raw_tokens;
        state.stats.out_tokens += if result.out_tokens > 0 {
            result.out_tokens
        } else {
            result.raw_tokens
        };
        result
    }

    /// The text the model should read.
    pub fn optimize(&self, text: &str, attrs: &Attrs) -> String {
        self.optimize_result(text, attrs).text
    }

    /// The original behind an optimized result; empty when unavailable.
    pub fn raw(&self, raw_id: &str) -> String {
        if !self.ready() {
            return String::new();
        }
        let url = format!("{}/sdk/v1/raw/{raw_id}", base_url());
        ureq::get(&url)
            .timeout(self.timeout)
            .call()
            .ok()
            .and_then(|response| response.into_string().ok())
            .unwrap_or_default()
    }

    /// Base URL that routes an LLM client through the gascoigne proxy, or `None` in bypass.
    /// `api` is "openai" (`/v1`), "anthropic" or "gemini".
    pub fn proxy_base_url(&self, api: &str) -> Option<String> {
        if !self.ready() {
            return None;
        }
        let base = base_url();
        Some(if api == "openai" {
            format!("{base}/v1")
        } else {
            base
        })
    }

    /// Tokens (estimated) before and after, summed over this runtime's calls.
    pub fn stats(&self) -> Stats {
        self.state().stats
    }

    /// Wrap a tool function so the string it returns is optimized.
    pub fn wrap_tool<'a, A>(
        &'a self,
        name: &str,
        tool: impl Fn(A) -> String + 'a,
    ) -> impl Fn(A) -> String + 'a {
        let attrs = Attrs::tool(name);
        move |arg| self.optimize(&tool(arg), &attrs)
    }
}
