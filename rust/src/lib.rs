//! Embed gascoigne token optimization in agent frameworks.
//!
//! Every call is safe: when the gascoigne CLI is missing or the server misbehaves, inputs come back
//! unchanged and no error reaches the caller.

mod native;

pub use native::{Price, Pricing, Settings};

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

/// The recorded runs of one group, summed.
#[derive(Debug, Clone, Default, PartialEq, Eq, Deserialize)]
#[serde(default)]
pub struct Total {
    pub group: String,
    pub runs: u64,
    pub optimized: u64,
    pub failed: u64,
    pub raw_tokens: u64,
    pub out_tokens: u64,
    pub saved: i64,
    /// RFC 3339, empty when unknown.
    pub first: String,
    pub last: String,
}

/// One recorded optimization.
#[derive(Debug, Clone, Default, PartialEq, Eq, Deserialize)]
#[serde(default)]
pub struct Run {
    /// Run id, for paging with [`RunsQuery::before`].
    pub id: u64,
    /// RFC 3339.
    pub time: String,
    pub session: String,
    pub agent: String,
    pub model: String,
    pub command: String,
    pub route: String,
    pub optimizers: Vec<String>,
    pub raw_tokens: u64,
    pub out_tokens: u64,
    pub duration_ns: i64,
    /// Id of the stored original, see [`Runtime::raw`].
    pub raw_id: String,
    /// `optimized`, `unchanged`, `bypassed`, `rerequested` or `error`.
    pub outcome: String,
    pub reason: String,
}

/// The tokens saved, priced for one model.
#[derive(Debug, Clone, Default, PartialEq, Deserialize)]
#[serde(default)]
pub struct ModelCost {
    pub model: String,
    /// Where the price comes from: `built-in`, `static`, `json`, `api` or `script`.
    pub source: String,
    pub assumed: bool,
    pub tokenizer: String,
    /// Saved, in gascoigne's estimate units.
    pub tokens: u64,
    /// Saved, in the model's own tokens.
    pub model_tokens: u64,
    pub first_read_usd: f64,
    pub in_context_usd: f64,
}

/// What the tokens saved are worth: an estimate from list prices or the prices configured for
/// gascoigne, not what anyone is billed. With `billing == "subscription"` there are no dollars.
#[derive(Debug, Clone, Default, PartialEq, Deserialize)]
#[serde(default)]
pub struct Costs {
    pub billing: String,
    pub first_read_usd: f64,
    pub in_context_usd: f64,
    pub rereads: f64,
    pub savings: Vec<ModelCost>,
    pub unpriced: Vec<String>,
}

/// Filters for [`Runtime::totals`] and [`Runtime::costs`]; empty ones match everything.
#[derive(Debug, Clone, Default)]
pub struct TotalsQuery {
    /// `route` (default), `session`, `family`, `optimizer`, `command`, `outcome`, `agent`,
    /// `model`, `day`, `week` or `month`; totals only.
    pub by: String,
    pub session: String,
    pub agent: String,
    pub model: String,
    /// Only runs from this RFC 3339 time on.
    pub since: String,
}

/// Filters for [`Runtime::runs`], newest first.
#[derive(Debug, Clone, Default)]
pub struct RunsQuery {
    pub session: String,
    pub agent: String,
    pub model: String,
    /// Only runs from this RFC 3339 time on.
    pub since: String,
    /// A run id: only older runs come back, to page; 0 for none.
    pub before: u64,
    /// At most this many; 0 means 50, the most is 1000.
    pub limit: u32,
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
    native: Option<native::Native>,
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

    /// A runtime that runs the engine in this process through libgascoigne (crate feature
    /// `native`). `settings` is merged by the library over its defaults and the user's file.
    ///
    /// # Errors
    /// Fails when no library is found or it cannot be loaded; the message names where it looked.
    pub fn native(agent: &str, settings: Settings) -> std::result::Result<Self, String> {
        Self::native_at(agent, settings, None)
    }

    /// Like [`Runtime::native`], loading the library at `library` when given (the
    /// `gascoigne-native` crate passes the one it unpacked).
    ///
    /// # Errors
    /// As [`Runtime::native`].
    // Without the `native` feature the arguments are not used, which is the point of the stub.
    #[cfg_attr(not(feature = "native"), allow(clippy::needless_pass_by_value))]
    pub fn native_at(
        agent: &str,
        settings: Settings,
        library: Option<PathBuf>,
    ) -> std::result::Result<Self, String> {
        let runtime = Runtime::new(agent);
        runtime.state().native = Some(native::Native::open(&settings, library.as_deref())?);
        Ok(runtime)
    }

    /// Native when `$GASCOIGNE_MODE` is `native`, else a proxy runtime.
    ///
    /// # Errors
    /// As [`Runtime::native`], in native mode only.
    pub fn from_env(agent: &str, settings: Settings) -> std::result::Result<Self, String> {
        if env("GASCOIGNE_MODE") == "native" {
            Self::native(agent, settings)
        } else {
            Ok(Self::new(agent))
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
            let available =
                state.native.is_some() || healthy(&mut state) || start_server(&mut state);
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

    /// Runs the request in the embedded engine when there is one, else through the server.
    fn send(&self, request: &OptimizeRequest) -> Option<Result> {
        let state = self.state();
        let Some(native) = &state.native else {
            drop(state);
            return self.post(request);
        };
        let body = serde_json::to_string(request).ok()?;
        let out = native.optimize(&body).ok()?;
        serde_json::from_str::<Result>(&out)
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
        let Some(result) = self.send(&request) else {
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
        if let Some(native) = &self.state().native {
            return native.raw(raw_id).unwrap_or_default();
        }
        let url = format!("{}/sdk/v1/raw/{raw_id}", base_url());
        ureq::get(&url)
            .timeout(self.timeout)
            .call()
            .ok()
            .and_then(|response| response.into_string().ok())
            .unwrap_or_default()
    }

    /// The recorded runs summed per group. Reads never panic and never trip the optimize breaker:
    /// on any failure (bypass, server down, a bad query) the answer is empty.
    pub fn totals(&self, query: &TotalsQuery) -> Vec<Total> {
        let fields = [
            ("by", query.by.clone()),
            ("session", query.session.clone()),
            ("agent", query.agent.clone()),
            ("model", query.model.clone()),
            ("since", query.since.clone()),
        ];
        self.read("/sdk/v1/stats", &fields, native::Native::stats)
            .unwrap_or_default()
    }

    /// The recorded runs, newest first; empty on any failure.
    pub fn runs(&self, query: &RunsQuery) -> Vec<Run> {
        let number = |n: u64| if n > 0 { n.to_string() } else { String::new() };
        let fields = [
            ("session", query.session.clone()),
            ("agent", query.agent.clone()),
            ("model", query.model.clone()),
            ("since", query.since.clone()),
            ("before", number(query.before)),
            ("limit", number(u64::from(query.limit))),
        ];
        self.read("/sdk/v1/recent", &fields, native::Native::recent)
            .unwrap_or_default()
    }

    /// What the tokens saved are worth, an estimate not a bill; empty (`billing == ""`) on any
    /// failure. `by` of the query is ignored.
    pub fn costs(&self, query: &TotalsQuery) -> Costs {
        let fields = [
            ("session", query.session.clone()),
            ("agent", query.agent.clone()),
            ("model", query.model.clone()),
            ("since", query.since.clone()),
        ];
        self.read("/sdk/v1/costs", &fields, native::Native::costs)
            .unwrap_or_default()
    }

    /// A ledger read through the engine or the server; `None` on any failure.
    fn read<T: serde::de::DeserializeOwned>(
        &self,
        path: &str,
        fields: &[(&str, String)],
        via_engine: fn(&native::Native, &str) -> std::result::Result<String, String>,
    ) -> Option<T> {
        if !self.ready() {
            return None;
        }
        let set: Vec<(&str, &String)> = fields
            .iter()
            .filter(|(_, value)| !value.is_empty())
            .map(|(key, value)| (*key, value))
            .collect();
        if let Some(native) = &self.state().native {
            // The library takes before and limit as numbers.
            let doc: serde_json::Map<String, serde_json::Value> = set
                .iter()
                .map(|(key, value)| {
                    let json = match (*key, value.parse::<u64>()) {
                        ("before" | "limit", Ok(n)) => serde_json::Value::from(n),
                        _ => serde_json::Value::from((*value).clone()),
                    };
                    ((*key).to_string(), json)
                })
                .collect();
            let body = via_engine(native, &serde_json::Value::Object(doc).to_string()).ok()?;
            return serde_json::from_str(&body).ok();
        }
        let mut request = ureq::get(&format!("{}{path}", base_url())).timeout(self.timeout);
        for (key, value) in set {
            request = request.query(key, value);
        }
        request.call().ok()?.into_json().ok()
    }

    /// Base URL that routes an LLM client through the gascoigne proxy, or `None` in bypass.
    /// `api` is "openai" (`/v1`), "anthropic" or "gemini".
    pub fn proxy_base_url(&self, api: &str) -> Option<String> {
        // The embedded engine has no listening proxy.
        if !self.ready() || self.state().native.is_some() {
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
