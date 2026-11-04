package gascoigne

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

// ledgerServer answers the three ledger routes and records the last query string.
func ledgerServer(t *testing.T, status int) *string {
	t.Helper()
	var last string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		last = r.URL.Path + "?" + r.URL.RawQuery
		if r.URL.Path == "/sdk/v1/health" {
			_ = json.NewEncoder(w).Encode(map[string]any{"version": "t", "proto": 1})
			return
		}
		if status != http.StatusOK {
			http.Error(w, "boom", status)
			return
		}
		switch r.URL.Path {
		case "/sdk/v1/stats":
			total := Total{Group: "sdk", Runs: 2, RawTokens: 100, OutTokens: 40, Saved: 60}
			_ = json.NewEncoder(w).Encode([]Total{total})
		case "/sdk/v1/recent":
			run := Run{ID: 7, Session: "s1", RawID: "abc", Outcome: "optimized"}
			_ = json.NewEncoder(w).Encode([]Run{run})
		case "/sdk/v1/costs":
			costs := Costs{Billing: "api", InContextUSD: 1.5}
			costs.Savings = []ModelCost{{Model: "m", Source: "static"}}
			_ = json.NewEncoder(w).Encode(costs)
		}
	}))
	t.Cleanup(srv.Close)
	t.Setenv("GASCOIGNE_SERVER_ADDR", strings.TrimPrefix(srv.URL, "http://"))
	return &last
}

func TestLedgerReadsThroughTheServer(t *testing.T) {
	clean(t)
	last := ledgerServer(t, http.StatusOK)
	rt := New(Options{})
	ctx := context.Background()

	since := time.Date(2026, 11, 1, 0, 0, 0, 0, time.UTC)
	totals, err := rt.Totals(ctx, TotalsQuery{By: "agent", Session: "s 1", Since: since})
	if err != nil || len(totals) != 1 || totals[0].Saved != 60 {
		t.Fatalf("totals = %+v, %v", totals, err)
	}
	if want := "/sdk/v1/stats?by=agent&session=s+1&since=2026-11-01T00%3A00%3A00Z"; *last != want {
		t.Fatalf("query = %s, want %s", *last, want)
	}
	runs, err := rt.Runs(ctx, RunsQuery{Session: "s1", Limit: 5, Before: 9})
	if err != nil || len(runs) != 1 || runs[0].RawID != "abc" {
		t.Fatalf("runs = %+v, %v", runs, err)
	}
	if want := "/sdk/v1/recent?before=9&limit=5&session=s1"; *last != want {
		t.Fatalf("query = %s, want %s", *last, want)
	}
	costs, err := rt.Costs(ctx, TotalsQuery{})
	if err != nil || costs.InContextUSD != 1.5 || costs.Savings[0].Source != "static" {
		t.Fatalf("costs = %+v, %v", costs, err)
	}
}

func TestLedgerReadFailureIsAnErrorNotAPanicAndSkipsTheBreaker(t *testing.T) {
	clean(t)
	ledgerServer(t, http.StatusInternalServerError)
	rt := New(Options{})
	ctx := context.Background()
	// A failing read must not open the optimize breaker.
	for range 10 {
		if _, err := rt.Totals(ctx, TotalsQuery{}); err == nil {
			t.Fatal("server error not reported")
		}
	}
	if !rt.Ready(ctx) {
		t.Fatal("ledger reads tripped the optimize breaker")
	}
}

func TestLedgerReadsInBypassAreEmptyWithAnError(t *testing.T) {
	clean(t)
	t.Setenv("GASCOIGNE_SDK", "off")
	rt := New(Options{})
	if got, err := rt.Totals(context.Background(), TotalsQuery{}); err == nil || got != nil {
		t.Fatalf("bypass: %+v, %v", got, err)
	}
	if got, err := rt.Costs(context.Background(), TotalsQuery{}); err == nil || got.Billing != "" {
		t.Fatalf("bypass: %+v, %v", got, err)
	}
}

// ledgerBackend is an embedded engine that also answers ledger reads.
type ledgerBackend struct{ plainBackend }

func (ledgerBackend) Totals(context.Context, TotalsQuery) ([]Total, error) {
	return []Total{{Group: "embedded", Runs: 1}}, nil
}
func (ledgerBackend) Runs(context.Context, RunsQuery) ([]Run, error) { return []Run{{ID: 1}}, nil }
func (ledgerBackend) Costs(context.Context, TotalsQuery) (Costs, error) {
	return Costs{Billing: "subscription"}, nil
}

type plainBackend struct{}

func (plainBackend) Optimize(context.Context, Request) (Result, error) { return Result{}, nil }
func (plainBackend) Raw(context.Context, string) (string, error)       { return "", nil }
func (plainBackend) Close() error                                      { return nil }

func TestLedgerReadsThroughAnEmbeddedBackend(t *testing.T) {
	clean(t)
	rt := New(Options{Backend: ledgerBackend{}})
	ctx := context.Background()
	if totals, err := rt.Totals(ctx, TotalsQuery{}); err != nil || totals[0].Group != "embedded" {
		t.Fatalf("totals = %+v, %v", totals, err)
	}
	if costs, err := rt.Costs(ctx, TotalsQuery{}); err != nil || costs.Billing != "subscription" {
		t.Fatalf("costs = %+v, %v", costs, err)
	}
	// A backend without ledger reads says so.
	plain := New(Options{Backend: plainBackend{}})
	_, err := plain.Totals(ctx, TotalsQuery{})
	if err == nil || !strings.Contains(err.Error(), "ledger") {
		t.Fatalf("plain backend: %v", err)
	}
}
