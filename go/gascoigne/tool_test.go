package gascoigne

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

// rawFixture is a real original captured from a gascoigne server.
func rawFixture(t *testing.T) string {
	t.Helper()
	b, err := os.ReadFile(filepath.Join("..", "..", "spec", "fixtures", "raw.txt"))
	if err != nil {
		t.Fatal(err)
	}
	return string(b)
}

type namedTool struct {
	out string
	err error
}

func (namedTool) Name() string        { return "search_logs" }
func (namedTool) Description() string { return "finds logs" }
func (n namedTool) Call(context.Context, string) (string, error) {
	return n.out, n.err
}

// The wrapper keeps the tool's name and description and tags the request with the tool name.
func TestWrapToolKeepsIdentityAndSendsToolName(t *testing.T) {
	clean(t)
	f := &fakeServer{proto: 1, status: 200}
	f.serve(t)
	rt := New(Options{})
	original := rawFixture(t)
	w := rt.WrapTool(namedTool{out: original})
	if w.Name() != "search_logs" || w.Description() != "finds logs" {
		t.Fatalf("identity lost: %q %q", w.Name(), w.Description())
	}
	got, err := w.Call(context.Background(), "q")
	if err != nil || got != "short" {
		t.Fatalf("got %q, %v", got, err)
	}
	if f.last.Tool != "search_logs" || f.last.Text != original {
		t.Fatalf("server saw tool=%q, text matches=%v", f.last.Tool, f.last.Text == original)
	}
}

// A tool error passes through untouched and nothing is sent to the server.
func TestWrapToolErrorSkipsOptimize(t *testing.T) {
	clean(t)
	f := &fakeServer{proto: 1, status: 200}
	f.serve(t)
	rt := New(Options{})
	boom := errors.New("boom")
	got, err := rt.WrapTool(namedTool{out: "partial", err: boom}).Call(context.Background(), "")
	if !errors.Is(err, boom) || got != "partial" {
		t.Fatalf("got %q, %v", got, err)
	}
	if n := f.posts.Load(); n != 0 {
		t.Fatalf("%d optimize calls, want 0", n)
	}
}

// WrapFunc names the request after the function and also lets errors through unoptimized.
func TestWrapFuncSendsNameAndPassesErrors(t *testing.T) {
	clean(t)
	f := &fakeServer{proto: 1, status: 200}
	f.serve(t)
	rt := New(Options{})
	ctx := context.Background()
	original := rawFixture(t)
	ok := WrapFunc(rt, "grep_logs", func(context.Context, int) (string, error) {
		return original, nil
	})
	if got, err := ok(ctx, 1); err != nil || got != "short" {
		t.Fatalf("got %q, %v", got, err)
	}
	if f.last.Tool != "grep_logs" {
		t.Fatalf("tool = %q", f.last.Tool)
	}
	boom := errors.New("boom")
	bad := WrapFunc(rt, "grep_logs", func(context.Context, int) (string, error) {
		return "x", boom
	})
	before := f.posts.Load()
	if got, err := bad(ctx, 1); !errors.Is(err, boom) || got != "x" {
		t.Fatalf("got %q, %v", got, err)
	}
	if f.posts.Load() != before {
		t.Fatal("error result was sent to the server")
	}
}

// Empty output is returned as is, without a server call.
func TestWrapToolEmptyOutputNotSent(t *testing.T) {
	clean(t)
	f := &fakeServer{proto: 1, status: 200}
	f.serve(t)
	rt := New(Options{})
	got, err := rt.WrapTool(namedTool{}).Call(context.Background(), "")
	if err != nil || got != "" || f.posts.Load() != 0 {
		t.Fatalf("got %q, %v, posts %d", got, err, f.posts.Load())
	}
}
