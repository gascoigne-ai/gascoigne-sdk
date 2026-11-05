package core

import (
	"encoding/json"
	"path/filepath"
	"strings"
	"testing"
)

func options(t *testing.T) string {
	t.Helper()
	db := filepath.Join(t.TempDir(), "l.db")
	body, _ := json.Marshal(Options{
		IgnoreUserFile: true,
		Config:         "extensions:\n  ledger:\n    path: " + db + "\n",
	})
	return string(body)
}

func TestOptimizeAndRawRoundTrip(t *testing.T) {
	h, err := Open(options(t))
	if err != nil {
		t.Fatal(err)
	}
	defer Close(h)
	raw := strings.Repeat("INFO request served path=/api/items status=200 ms=12\n", 400)
	req, _ := json.Marshal(Request{Text: raw, Tool: "bash", Cmd: "tail -n 400 app.log"})
	out, err := Optimize(h, string(req))
	if err != nil {
		t.Fatal(err)
	}
	var res Response
	if err := json.Unmarshal([]byte(out), &res); err != nil {
		t.Fatal(err)
	}
	if res.OutTokens >= res.RawTokens || res.RawID == "" {
		t.Fatalf("not optimized: %+v", res)
	}
	if got, err := Raw(h, res.RawID); err != nil || got != raw {
		t.Fatalf("Raw: %d bytes, %v", len(got), err)
	}
}

func TestClosedHandleIsAnErrorNotAPanic(t *testing.T) {
	h, err := Open(options(t))
	if err != nil {
		t.Fatal(err)
	}
	if err := Close(h); err != nil {
		t.Fatal(err)
	}
	if _, err := Optimize(h, `{"text":"x"}`); err == nil {
		t.Fatal("closed handle accepted")
	}
	if _, err := Open(`{not json`); err == nil {
		t.Fatal("bad options accepted")
	}
}

func memoryOptions(t *testing.T, extra func(*Options)) string {
	t.Helper()
	t.Setenv("GASCOIGNE_LEDGER", "")
	t.Setenv("XDG_DATA_HOME", t.TempDir())
	o := Options{IgnoreUserFile: true, Ledger: "memory"}
	if extra != nil {
		extra(&o)
	}
	body, _ := json.Marshal(o)
	return string(body)
}

func optimizeLog(t *testing.T, h Handle, session string) {
	t.Helper()
	raw := strings.Repeat("INFO request served path=/api/items status=200 ms=12\n", 400)
	req, _ := json.Marshal(Request{
		Text: raw, Tool: "bash", Cmd: "tail -n 400 app.log",
		Session: session, Agent: "sdk", Model: "acme-large",
	})
	if _, err := Optimize(h, string(req)); err != nil {
		t.Fatal(err)
	}
}

func TestMemoryLedgerStatsAndRecent(t *testing.T) {
	h, err := Open(memoryOptions(t, nil))
	if err != nil {
		t.Fatal(err)
	}
	defer Close(h)
	optimizeLog(t, h, "s1")
	optimizeLog(t, h, "s2")

	body, err := Stats(h, `{"by":"agent"}`)
	if err != nil {
		t.Fatal(err)
	}
	var stats []struct {
		Group string `json:"group"`
		Runs  int    `json:"runs"`
		Saved int    `json:"saved"`
	}
	err = json.Unmarshal([]byte(body), &stats)
	if err != nil || len(stats) != 1 || stats[0].Group != "sdk" || stats[0].Runs != 2 ||
		stats[0].Saved <= 0 {
		t.Fatalf("stats = %s, %v", body, err)
	}
	body, err = Recent(h, `{"session":"s1","limit":5}`)
	if err != nil {
		t.Fatal(err)
	}
	var runs []struct {
		Session string `json:"session"`
		RawID   string `json:"raw_id"`
	}
	err = json.Unmarshal([]byte(body), &runs)
	if err != nil || len(runs) != 1 || runs[0].Session != "s1" || runs[0].RawID == "" {
		t.Fatalf("recent = %s, %v", body, err)
	}
	// An empty query document is allowed, a bad one is an error, not a panic.
	if _, err := Stats(h, ""); err != nil {
		t.Fatalf("empty query: %v", err)
	}
	for _, bad := range []string{`{`, `{"by":"nonsense"}`, `{"since":"yesterday"}`} {
		if _, err := Stats(h, bad); err == nil {
			t.Errorf("stats query %q accepted", bad)
		}
	}
	if _, err := Recent(h, `{"limit":-1}`); err != nil {
		t.Fatalf("a negative limit means the default: %v", err)
	}
}

func TestLedgerOptionIsValidated(t *testing.T) {
	for _, bad := range []string{`{"ledger":"disk"}`} {
		if h, err := Open(bad); err == nil {
			Close(h)
			t.Errorf("options %s accepted", bad)
		}
	}
}

func TestStatsOfAHandleWithoutRunsIsEmptyList(t *testing.T) {
	h, err := Open(memoryOptions(t, nil))
	if err != nil {
		t.Fatal(err)
	}
	defer Close(h)
	calls := map[string]func(Handle, string) (string, error){"stats": Stats, "recent": Recent}
	for name, call := range calls {
		body, err := call(h, `{}`)
		if err != nil || body != "[]" {
			t.Errorf("%s = %q, %v; want []", name, body, err)
		}
	}
}

func TestStatsOnClosedHandleIsAnError(t *testing.T) {
	h, _ := Open(memoryOptions(t, nil))
	Close(h)
	for _, call := range []func(Handle, string) (string, error){Stats, Recent} {
		if _, err := call(h, `{}`); err == nil {
			t.Fatal("closed handle accepted")
		}
	}
}
