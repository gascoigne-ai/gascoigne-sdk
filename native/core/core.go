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
const ABIVersion = 1

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
	return inproc.Options{
		Config: o.Config, Set: o.Set, Only: o.Only, Disable: o.Disable,
		IgnoreUserFile: o.IgnoreUserFile,
	}
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
