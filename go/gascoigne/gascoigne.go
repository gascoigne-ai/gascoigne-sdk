// Package gascoigne embeds gascoigne token optimization in agent frameworks.
//
// Every call is safe: when the gascoigne CLI is missing or the server misbehaves, inputs come back
// unchanged and no error reaches the caller.
package gascoigne

import (
	"bytes"
	"cmp"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"os/exec"
	"sync"
	"time"
)

const (
	proto           = 1
	defaultAddr     = "127.0.0.1:7878"
	installHint     = "mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne"
	breakerFailures = 5
	breakerPause    = 60 * time.Second
)

// Result is one optimize call: Text is what the model should read.
type Result struct {
	Text      string `json:"text"`
	RawID     string `json:"raw_id"`
	RawTokens int    `json:"raw_tokens"`
	OutTokens int    `json:"out_tokens"`
	Skipped   string `json:"skipped"`
}

// Attrs describe where the text came from; empty fields are left out.
type Attrs struct {
	Tool, Cmd, URL, Query, Model string
}

// optimizeRequest is the body of POST /sdk/v1/optimize.
type optimizeRequest struct {
	Text    string `json:"text"`
	Agent   string `json:"agent,omitempty"`
	Session string `json:"session,omitempty"`
	Tool    string `json:"tool,omitempty"`
	Cmd     string `json:"cmd,omitempty"`
	URL     string `json:"url,omitempty"`
	Query   string `json:"query,omitempty"`
	Model   string `json:"model,omitempty"`
}

// health is the response of GET /sdk/v1/health.
type health struct {
	Version string `json:"version"`
	Proto   int    `json:"proto"`
}

type availability int

const (
	unknown availability = iota
	available
	unavailable
)

// Options configure a Runtime. The zero value works.
type Options struct {
	Agent, Session string
	// per call, default 5s
	Timeout time.Duration
	// OnResult sees (original, result) after each optimized call.
	OnResult func(original string, r Result)
	Logger   *slog.Logger
}

// Runtime finds the CLI, makes sure its server runs, and optimizes text through it.
type Runtime struct {
	opts   Options
	client *http.Client

	mu         sync.Mutex
	state      availability
	failures   int
	pausedTill time.Time
	warned     bool
	rawTokens  int
	outTokens  int
}

// New returns a Runtime.
func New(opts Options) *Runtime {
	if opts.Timeout == 0 {
		opts.Timeout = 5 * time.Second
	}
	if opts.Logger == nil {
		opts.Logger = slog.Default()
	}
	return &Runtime{opts: opts, client: &http.Client{Timeout: opts.Timeout}}
}

func (r *Runtime) addr() string {
	if a := os.Getenv("GASCOIGNE_SERVER_ADDR"); a != "" {
		return a
	}
	return defaultAddr
}

func (r *Runtime) baseURL() string { return "http://" + r.addr() }

func (r *Runtime) disabled() bool {
	return os.Getenv("GASCOIGNE_SDK") == "off" || os.Getenv("GASCOIGNE_SERVER") == "off"
}

// warn logs once per Runtime; callers hold r.mu.
func (r *Runtime) warn(msg string) {
	if !r.warned {
		r.warned = true
		r.opts.Logger.Warn("gascoigne: " + msg)
	}
}

func (r *Runtime) healthy(ctx context.Context) bool {
	ctx, cancel := context.WithTimeout(ctx, 500*time.Millisecond)
	defer cancel()
	req, _ := http.NewRequestWithContext(ctx, http.MethodGet, r.baseURL()+"/sdk/v1/health", nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return false
	}
	defer func() { _ = resp.Body.Close() }()
	var h health
	if resp.StatusCode != http.StatusOK || json.NewDecoder(resp.Body).Decode(&h) != nil {
		return false
	}
	if h.Proto != proto {
		r.warn(fmt.Sprintf("server speaks proto %d, SDK %d; running without optimization",
			h.Proto, proto))
		return false
	}
	return true
}

func (r *Runtime) startServer(ctx context.Context) bool {
	exe := os.Getenv("GASCOIGNE_BIN")
	if exe == "" {
		var err error
		if exe, err = exec.LookPath("gascoigne"); err != nil {
			r.warn("gascoigne-cli not found on PATH; running without optimization. Install: " +
				installHint)
			return false
		}
	}
	sctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	if err := exec.CommandContext(sctx, exe, "server", "start").Run(); err != nil {
		r.warn(fmt.Sprintf("could not start gascoigne server (%v); running without optimization",
			err))
		return false
	}
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		if r.healthy(ctx) {
			return true
		}
		time.Sleep(100 * time.Millisecond)
	}
	r.warn("gascoigne server did not come up; running without optimization")
	return false
}

// Ready reports whether optimize calls will be tried. It probes once, then remembers.
func (r *Runtime) Ready(ctx context.Context) bool {
	if r.disabled() {
		return false
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.state == unknown {
		r.state = unavailable
		if r.healthy(ctx) || r.startServer(ctx) {
			r.state = available
		}
	}
	return r.state == available && time.Now().After(r.pausedTill)
}

func (r *Runtime) failed(err error) {
	r.opts.Logger.Debug("gascoigne optimize failed", "err", err)
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.failures++; r.failures >= breakerFailures {
		r.failures = 0
		r.pausedTill = time.Now().Add(breakerPause)
	}
}

// OptimizeResult optimizes text; on any problem the result carries the input unchanged.
func (r *Runtime) OptimizeResult(ctx context.Context, text string, a Attrs) Result {
	same := Result{Text: text}
	if text == "" || !r.Ready(ctx) {
		return same
	}
	body, err := json.Marshal(optimizeRequest{
		Text: text, Agent: r.opts.Agent, Session: r.opts.Session,
		Tool: a.Tool, Cmd: a.Cmd, URL: a.URL, Query: a.Query, Model: a.Model,
	})
	if err != nil {
		return same
	}
	url := r.baseURL() + "/sdk/v1/optimize"
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return same
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := r.client.Do(req)
	if err != nil {
		r.failed(err)
		return same
	}
	defer func() { _ = resp.Body.Close() }()
	var out Result
	if resp.StatusCode != http.StatusOK {
		r.failed(fmt.Errorf("status %s", resp.Status))
		return same
	}
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil || out.Text == "" {
		r.failed(fmt.Errorf("bad response: %w", err))
		return same
	}
	r.mu.Lock()
	r.failures = 0
	r.rawTokens += out.RawTokens
	r.outTokens += cmp.Or(out.OutTokens, out.RawTokens)
	r.mu.Unlock()
	if r.opts.OnResult != nil {
		r.opts.OnResult(text, out)
	}
	return out
}

// Optimize returns the text the model should read.
func (r *Runtime) Optimize(ctx context.Context, text string, a Attrs) string {
	return r.OptimizeResult(ctx, text, a).Text
}

// Raw returns the original behind an optimized result; empty when unavailable.
func (r *Runtime) Raw(ctx context.Context, rawID string) string {
	if !r.Ready(ctx) {
		return ""
	}
	url := r.baseURL() + "/sdk/v1/raw/" + rawID
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return ""
	}
	resp, err := r.client.Do(req)
	if err != nil {
		r.failed(err)
		return ""
	}
	defer func() { _ = resp.Body.Close() }()
	b, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return ""
	}
	return string(b)
}

// ProxyBaseURL routes an LLM client through the gascoigne proxy: api is "openai" (the /v1 root),
// "anthropic" or "gemini". Empty in bypass.
func (r *Runtime) ProxyBaseURL(ctx context.Context, api string) string {
	if !r.Ready(ctx) {
		return ""
	}
	if api == "openai" {
		return r.baseURL() + "/v1"
	}
	return r.baseURL()
}

// Stats are tokens (estimated) before and after, summed over this Runtime's calls.
func (r *Runtime) Stats() (rawTokens, outTokens int) {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.rawTokens, r.outTokens
}
