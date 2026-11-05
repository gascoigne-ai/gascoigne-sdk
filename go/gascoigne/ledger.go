package gascoigne

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"time"
)

// Total is the sum of the recorded runs of one group.
type Total struct {
	Group     string    `json:"group"`
	Runs      int       `json:"runs"`
	Optimized int       `json:"optimized"`
	Failed    int       `json:"failed"`
	RawTokens int       `json:"raw_tokens"`
	OutTokens int       `json:"out_tokens"`
	Saved     int       `json:"saved"`
	First     time.Time `json:"first,omitzero"`
	Last      time.Time `json:"last,omitzero"`
}

// Run is one recorded optimization.
type Run struct {
	ID         uint          `json:"id"`
	Time       time.Time     `json:"time"`
	Session    string        `json:"session,omitempty"`
	Agent      string        `json:"agent,omitempty"`
	Model      string        `json:"model,omitempty"`
	Command    string        `json:"command,omitempty"`
	Route      string        `json:"route,omitempty"`
	Optimizers []string      `json:"optimizers,omitempty"`
	RawTokens  int           `json:"raw_tokens"`
	OutTokens  int           `json:"out_tokens"`
	Duration   time.Duration `json:"duration_ns"`
	RawID      string        `json:"raw_id,omitempty"`
	Outcome    string        `json:"outcome"`
	Reason     string        `json:"reason,omitempty"`
}

// TotalsQuery selects what Totals sums. Empty fields match everything. By is one of route,
// session, family, optimizer, command, outcome, agent, model, day, week or month (empty means
// route).
type TotalsQuery struct {
	By, Session, Agent, Model string
	Since                     time.Time
}

// RunsQuery selects recorded runs, newest first. Before is a run ID: only older runs come back,
// to page. Limit 0 means 50 and the most is 1000.
type RunsQuery struct {
	Session, Agent, Model string
	Since                 time.Time
	Before                uint
	Limit                 int
}

// LedgerBackend is implemented by a Backend that can also answer ledger reads (the embedded
// engine does). A Backend without it makes Totals and Runs return ErrNoLedger.
type LedgerBackend interface {
	Totals(ctx context.Context, q TotalsQuery) ([]Total, error)
	Runs(ctx context.Context, q RunsQuery) ([]Run, error)
}

// ErrNoLedger means there is nothing to read: gascoigne is off or missing, or the embedded
// Backend does not expose its ledger.
var ErrNoLedger = errors.New("gascoigne: ledger not available")

func (q TotalsQuery) values() url.Values {
	v := url.Values{}
	set := func(key, value string) {
		if value != "" {
			v.Set(key, value)
		}
	}
	set("by", q.By)
	set("session", q.Session)
	set("agent", q.Agent)
	set("model", q.Model)
	if !q.Since.IsZero() {
		v.Set("since", q.Since.UTC().Format(time.RFC3339))
	}
	return v
}

func (q RunsQuery) values() url.Values {
	v := TotalsQuery{Session: q.Session, Agent: q.Agent, Model: q.Model, Since: q.Since}.values()
	if q.Before > 0 {
		v.Set("before", strconv.FormatUint(uint64(q.Before), 10))
	}
	if q.Limit > 0 {
		v.Set("limit", strconv.Itoa(q.Limit))
	}
	return v
}

// Totals sums the recorded runs per group. A failure returns the error and leaves the optimize
// breaker alone: the application asked for these numbers, so it should hear why it has none.
func (r *Runtime) Totals(ctx context.Context, q TotalsQuery) ([]Total, error) {
	if r.opts.Backend != nil {
		backend, ok := r.opts.Backend.(LedgerBackend)
		if !ok || !r.Ready(ctx) {
			return nil, ErrNoLedger
		}
		return backend.Totals(ctx, q)
	}
	var out []Total
	return out, r.read(ctx, "/sdk/v1/stats", q.values(), &out)
}

// Runs lists the recorded runs, newest first.
func (r *Runtime) Runs(ctx context.Context, q RunsQuery) ([]Run, error) {
	if r.opts.Backend != nil {
		backend, ok := r.opts.Backend.(LedgerBackend)
		if !ok || !r.Ready(ctx) {
			return nil, ErrNoLedger
		}
		return backend.Runs(ctx, q)
	}
	var out []Run
	return out, r.read(ctx, "/sdk/v1/recent", q.values(), &out)
}

// read GETs a ledger route from the server into out.
func (r *Runtime) read(ctx context.Context, path string, query url.Values, out any) error {
	if !r.Ready(ctx) {
		return ErrNoLedger
	}
	address := r.baseURL() + path
	if len(query) > 0 {
		address += "?" + query.Encode()
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, address, nil)
	if err != nil {
		return err
	}
	response, err := r.client.Do(request)
	if err != nil {
		return err
	}
	defer func() { _ = response.Body.Close() }()
	if response.StatusCode != http.StatusOK {
		message, _ := io.ReadAll(io.LimitReader(response.Body, 512))
		return fmt.Errorf("gascoigne: %s: %s: %s", path, response.Status, message)
	}
	if err := json.NewDecoder(response.Body).Decode(out); err != nil {
		return fmt.Errorf("gascoigne: %s: bad response: %w", path, err)
	}
	return nil
}
