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
