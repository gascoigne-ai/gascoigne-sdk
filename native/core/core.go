// Package core is the logic behind the C ABI of gascoigne-sdk: JSON strings in, JSON strings out,
// engines referred to by handle. It has no cgo, so it can be tested with plain `go test`.
//
// Configuration lives here and in the engine it wraps, not in the host language: the host sends
// an Options document and this library merges it over the built-in defaults and the user's file.
package core

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/gascoigne-ai/gascoigne-cli/inproc"
)

// ABIVersion changes when an exported function or a JSON field changes incompatibly.
//
// 2 added gascoigne_stats, gascoigne_recent, gascoigne_costs and the ledger and pricing options.
// 3 drops costs and pricing: the SDK counts tokens only. Version 1 functions behave as before.
const ABIVersion = 3

// defaultTimeout bounds every optimize call unless Options say otherwise.
const defaultTimeout = 5 * time.Second

// Handle names an open engine. Zero is never valid.
type Handle uint64

// Options is the JSON document the host passes to Open. Every field is optional.
type Options struct {
	// Config is YAML merged over the defaults and the user's file.
	Config string `json:"config,omitempty"`
	// Set holds "dotted.path=value" assignments applied last.
	Set []string `json:"set,omitempty"`
	// Only keeps just these optimizers in every chain.
	Only []string `json:"only,omitempty"`
	// Disable drops these optimizers from every chain.
	Disable []string `json:"disable,omitempty"`
	// IgnoreUserFile skips the user's config file.
	IgnoreUserFile bool `json:"ignore_user_file,omitempty"`
	// TimeoutMS bounds each optimize call; zero means five seconds.
	TimeoutMS int `json:"timeout_ms,omitempty"`
	// Ledger is "file" (default: the configured sqlite file) or "memory" (private to this
	// process, gone at close).
	Ledger string `json:"ledger,omitempty"`
}

// Request is the JSON document of one optimize call.
type Request struct {
	Text    string `json:"text"`
	Tool    string `json:"tool,omitempty"`
	Cmd     string `json:"cmd,omitempty"`
	URL     string `json:"url,omitempty"`
	Query   string `json:"query,omitempty"`
	Session string `json:"session,omitempty"`
	Agent   string `json:"agent,omitempty"`
	Model   string `json:"model,omitempty"`
}

// Response is the JSON document an optimize call returns; it matches the /sdk/v1 wire body.
type Response struct {
	Text      string `json:"text"`
	RawID     string `json:"raw_id,omitempty"`
	RawTokens int    `json:"raw_tokens"`
	OutTokens int    `json:"out_tokens"`
	Skipped   string `json:"skipped,omitempty"`
}

type entry struct {
	eng     *inproc.Engine
	timeout time.Duration
}

var (
	mu      sync.Mutex
	next    Handle
	engines = map[Handle]entry{}
)

func (o Options) engine() inproc.Options {
	engine := inproc.Options{
		Config: o.Config, Set: o.Set, Only: o.Only, Disable: o.Disable,
		IgnoreUserFile: o.IgnoreUserFile, Ledger: o.Ledger,
	}
	return engine
}

func parseOptions(doc string) (Options, error) {
	var o Options
	if doc == "" {
		return o, nil
	}
	if err := json.Unmarshal([]byte(doc), &o); err != nil {
		return o, fmt.Errorf("options: %w", err)
	}
	return o, nil
}

// Open starts an engine from an Options document and returns its handle.
func Open(optionsJSON string) (h Handle, err error) {
	defer recoverTo(&err)
	o, err := parseOptions(optionsJSON)
	if err != nil {
		return 0, err
	}
	eng, err := inproc.New(context.Background(), o.engine())
	if err != nil {
		return 0, err
	}
	timeout := defaultTimeout
	if o.TimeoutMS > 0 {
		timeout = time.Duration(o.TimeoutMS) * time.Millisecond
	}
	mu.Lock()
	defer mu.Unlock()
	next++
	engines[next] = entry{eng: eng, timeout: timeout}
	return next, nil
}

// Config returns the merged YAML an Options document describes, without starting anything.
func Config(optionsJSON string) (yaml string, err error) {
	defer recoverTo(&err)
	o, err := parseOptions(optionsJSON)
	if err != nil {
		return "", err
	}
	data, err := inproc.ConfigYAML(o.engine())
	return string(data), err
}

// Optimize runs a Request document and returns a Response document.
func Optimize(h Handle, requestJSON string) (out string, err error) {
	defer recoverTo(&err)
	e, err := lookup(h)
	if err != nil {
		return "", err
	}
	var req Request
	if err := json.Unmarshal([]byte(requestJSON), &req); err != nil {
		return "", fmt.Errorf("request: %w", err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), e.timeout)
	defer cancel()
	res, err := e.eng.Optimize(ctx, inproc.Request(req))
	if err != nil {
		return "", err
	}
	body, err := json.Marshal(Response(res))
	return string(body), err
}

// Raw returns the original text behind a raw id.
func Raw(h Handle, id string) (text string, err error) {
	defer recoverTo(&err)
	e, err := lookup(h)
	if err != nil {
		return "", err
	}
	ctx, cancel := context.WithTimeout(context.Background(), e.timeout)
	defer cancel()
	return e.eng.Raw(ctx, id)
}

// StatsQuery is the JSON document of Stats; every field is optional.
type StatsQuery struct {
	By      string `json:"by,omitempty"`
	Session string `json:"session,omitempty"`
	Agent   string `json:"agent,omitempty"`
	Model   string `json:"model,omitempty"`
	// Since is an RFC 3339 time.
	Since string `json:"since,omitempty"`
}

// RecentQuery is the JSON document of Recent; every field is optional.
type RecentQuery struct {
	Session string `json:"session,omitempty"`
	Agent   string `json:"agent,omitempty"`
	Model   string `json:"model,omitempty"`
	Since   string `json:"since,omitempty"`
	Before  uint   `json:"before,omitempty"`
	// Limit below 1 means 50; above 1000 means 1000.
	Limit int `json:"limit,omitempty"`
}

func parseSince(text string) (time.Time, error) {
	if text == "" {
		return time.Time{}, nil
	}
	since, err := time.Parse(time.RFC3339, text)
	if err != nil {
		return since, fmt.Errorf("since %q: want RFC 3339", text)
	}
	return since, nil
}

// query decodes a query document; an empty one means no filters.
func query[T any](doc string) (q T, err error) {
	if doc == "" {
		return q, nil
	}
	if err := json.Unmarshal([]byte(doc), &q); err != nil {
		return q, fmt.Errorf("query: %w", err)
	}
	return q, nil
}

// Stats totals the recorded runs per group and returns a JSON list.
func Stats(h Handle, queryJSON string) (out string, err error) {
	defer recoverTo(&err)
	e, err := lookup(h)
	if err != nil {
		return "", err
	}
	q, err := query[StatsQuery](queryJSON)
	if err != nil {
		return "", err
	}
	since, err := parseSince(q.Since)
	if err != nil {
		return "", err
	}
	ctx, cancel := context.WithTimeout(context.Background(), e.timeout)
	defer cancel()
	rows, err := e.eng.Stats(ctx, inproc.StatsQuery{
		By: q.By, Session: q.Session, Agent: q.Agent, Model: q.Model, Since: since,
	})
	return encodeList(rows, err)
}

// Recent lists the recorded runs, newest first, as a JSON list.
func Recent(h Handle, queryJSON string) (out string, err error) {
	defer recoverTo(&err)
	e, err := lookup(h)
	if err != nil {
		return "", err
	}
	q, err := query[RecentQuery](queryJSON)
	if err != nil {
		return "", err
	}
	since, err := parseSince(q.Since)
	if err != nil {
		return "", err
	}
	ctx, cancel := context.WithTimeout(context.Background(), e.timeout)
	defer cancel()
	rows, err := e.eng.Recent(ctx, inproc.RecentQuery{
		Session: q.Session, Agent: q.Agent, Model: q.Model, Since: since,
		Before: q.Before, Limit: q.Limit,
	})
	return encodeList(rows, err)
}

// encodeList marshals rows as a JSON list, [] when empty.
func encodeList[T any](rows []T, err error) (string, error) {
	if err != nil {
		return "", err
	}
	if rows == nil {
		rows = []T{}
	}
	body, err := json.Marshal(rows)
	return string(body), err
}

// Close stops an engine and forgets its handle. Closing an unknown handle is a no-op.
func Close(h Handle) (err error) {
	defer recoverTo(&err)
	mu.Lock()
	e, ok := engines[h]
	delete(engines, h)
	mu.Unlock()
	if !ok {
		return nil
	}
	return e.eng.Close(context.Background())
}

func lookup(h Handle) (entry, error) {
	mu.Lock()
	defer mu.Unlock()
	e, ok := engines[h]
	if !ok {
		return entry{}, errors.New("unknown or closed handle")
	}
	return e, nil
}

// recoverTo turns a panic into an error: a Go panic must never unwind into the host process.
func recoverTo(err *error) {
	if r := recover(); r != nil {
		*err = fmt.Errorf("gascoigne: internal panic: %v", r)
	}
}
