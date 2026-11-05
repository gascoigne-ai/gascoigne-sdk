package embedded

import (
	"context"
	"path/filepath"
	"strings"
	"testing"

	"github.com/gascoigne-ai/gascoigne-sdk/go/gascoigne"
)

func TestGoSDKRunsEmbedded(t *testing.T) {
	ctx := context.Background()
	db := filepath.Join(t.TempDir(), "l.db")
	b, err := New(ctx, Options{
		IgnoreUserFile: true,
		Config:         "extensions:\n  ledger:\n    path: " + db + "\n",
	})
	if err != nil {
		t.Fatal(err)
	}
	rt := gascoigne.New(gascoigne.Options{Backend: b})
	defer rt.Close()
	raw := strings.Repeat("INFO request served path=/api/items status=200 ms=12\n", 400)
	res := rt.OptimizeResult(ctx, raw, gascoigne.Attrs{Tool: "bash", Cmd: "tail app.log"})
	if res.OutTokens >= res.RawTokens || res.RawID == "" {
		t.Fatalf("not optimized: %+v", res)
	}
	if got := rt.Raw(ctx, res.RawID); got != raw {
		t.Fatalf("Raw returned %d bytes, want the original", len(got))
	}
}

func TestGoSDKReadsTheEmbeddedMemoryLedger(t *testing.T) {
	t.Setenv("GASCOIGNE_LEDGER", "")
	t.Setenv("XDG_DATA_HOME", t.TempDir())
	ctx := context.Background()
	b, err := New(ctx, Options{
		IgnoreUserFile: true, Ledger: "memory",
	})
	if err != nil {
		t.Fatal(err)
	}
	rt := gascoigne.New(gascoigne.Options{Backend: b, Agent: "sdk", Session: "s1"})
	defer rt.Close()
	raw := strings.Repeat("INFO request served path=/api/items status=200 ms=12\n", 400)
	attrs := gascoigne.Attrs{Tool: "bash", Cmd: "tail app.log", Model: "acme-large"}
	rt.OptimizeResult(ctx, raw, attrs)

	totals, err := rt.Totals(ctx, gascoigne.TotalsQuery{By: "agent"})
	if err != nil || len(totals) != 1 || totals[0].Group != "sdk" || totals[0].Runs != 1 ||
		totals[0].Saved <= 0 {
		t.Fatalf("totals = %+v, %v", totals, err)
	}
	runs, err := rt.Runs(ctx, gascoigne.RunsQuery{Session: "s1"})
	if err != nil || len(runs) != 1 || runs[0].RawID == "" || runs[0].Outcome != "optimized" {
		t.Fatalf("runs = %+v, %v", runs, err)
	}
	if _, err := rt.Totals(ctx, gascoigne.TotalsQuery{By: "nonsense"}); err == nil {
		t.Fatal("unknown grouping accepted")
	}
}
