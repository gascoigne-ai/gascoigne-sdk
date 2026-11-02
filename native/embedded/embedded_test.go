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
