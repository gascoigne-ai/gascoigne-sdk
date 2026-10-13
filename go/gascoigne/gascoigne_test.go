package gascoigne

import (
	"bytes"
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
)

type fakeServer struct {
	proto, status int
	posts         atomic.Int32
	last          optimizeRequest
}

func (f *fakeServer) serve(t *testing.T) {
	t.Helper()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/sdk/v1/health":
			_ = json.NewEncoder(w).Encode(map[string]any{"version": "t", "proto": f.proto})
		case "/sdk/v1/optimize":
			f.posts.Add(1)
			_ = json.NewDecoder(r.Body).Decode(&f.last)
			w.WriteHeader(f.status)
			_ = json.NewEncoder(w).Encode(Result{Text: "short", RawID: "abc", RawTokens: 100, OutTokens: 5})
		default:
			_, _ = w.Write([]byte("original"))
		}
	}))
	t.Cleanup(srv.Close)
	t.Setenv("GASCOIGNE_SERVER_ADDR", strings.TrimPrefix(srv.URL, "http://"))
}

func clean(t *testing.T) {
	t.Helper()
	for _, k := range []string{"GASCOIGNE_SDK", "GASCOIGNE_SERVER", "GASCOIGNE_BIN"} {
		t.Setenv(k, "")
	}
}

func TestMissingCLIWarnsOnceAndPassesThrough(t *testing.T) {
	clean(t)
	t.Setenv("GASCOIGNE_SERVER_ADDR", "127.0.0.1:9")
	t.Setenv("PATH", "")
	var buf bytes.Buffer
	rt := New(Options{Logger: slog.New(slog.NewTextHandler(&buf, nil))})
	ctx := context.Background()
	if got := rt.Optimize(ctx, "hello", Attrs{}); got != "hello" {
		t.Fatalf("got %q", got)
	}
	rt.Optimize(ctx, "again", Attrs{})
	if n := strings.Count(buf.String(), "not found on PATH"); n != 1 {
		t.Fatalf("%d warnings, want 1:\n%s", n, buf.String())
	}
	if rt.ProxyBaseURL(ctx, "openai") != "" || rt.Raw(ctx, "x") != "" {
		t.Fatal("bypass must return empty proxy URL and raw")
	}
}

func TestKillSwitch(t *testing.T) {
	clean(t)
	t.Setenv("GASCOIGNE_SDK", "off")
	if got := New(Options{}).Optimize(context.Background(), "x", Attrs{}); got != "x" {
		t.Fatalf("got %q", got)
	}
}

func TestOptimizesThroughServer(t *testing.T) {
	clean(t)
	f := &fakeServer{proto: 1, status: 200}
	f.serve(t)
	var seen string
	rt := New(Options{Agent: "demo", OnResult: func(_ string, r Result) { seen = r.RawID }})
	ctx := context.Background()
	res := rt.OptimizeResult(ctx, strings.Repeat("long ", 100), Attrs{Tool: "grep"})
	if res.Text != "short" || res.RawID != "abc" || seen != "abc" {
		t.Fatalf("res %+v seen %q", res, seen)
	}
	if f.last.Agent != "demo" || f.last.Tool != "grep" {
		t.Fatalf("request %v", f.last)
	}
	if raw, out := rt.Stats(); raw != 100 || out != 5 {
		t.Fatalf("stats %d %d", raw, out)
	}
	if rt.Raw(ctx, "abc") != "original" || !strings.HasSuffix(rt.ProxyBaseURL(ctx, "openai"), "/v1") {
		t.Fatal("raw or proxy url")
	}
}

func TestBreakerOpensAfterFiveFailures(t *testing.T) {
	clean(t)
	f := &fakeServer{proto: 1, status: 500}
	f.serve(t)
	rt := New(Options{})
	for range 7 {
		if got := rt.Optimize(context.Background(), "text", Attrs{}); got != "text" {
			t.Fatalf("got %q", got)
		}
	}
	if n := f.posts.Load(); n != 5 {
		t.Fatalf("%d posts, want 5", n)
	}
}

type stubTool struct{}

func (stubTool) Name() string                                 { return "t" }
func (stubTool) Description() string                          { return "d" }
func (stubTool) Call(context.Context, string) (string, error) { return "big", nil }

func TestWrapToolAndFunc(t *testing.T) {
	clean(t)
	f := &fakeServer{proto: 1, status: 200}
	f.serve(t)
	rt := New(Options{})
	ctx := context.Background()
	if got, _ := rt.WrapTool(stubTool{}).Call(ctx, ""); got != "short" {
		t.Fatalf("tool: %q", got)
	}
	fn := WrapFunc(rt, "f", func(context.Context, struct{}) (string, error) { return "big", nil })
	if got, _ := fn(ctx, struct{}{}); got != "short" {
		t.Fatalf("func: %q", got)
	}
}
