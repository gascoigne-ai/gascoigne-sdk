// Package kit holds everything a demo needs that is not about integrating gascoigne: env,
// OpenRouter settings, the noisy tool, and the report. Read the demos' main.go, not this file.
package kit

import (
	"bufio"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"slices"
	"strings"
	"time"

	"github.com/gascoigne-ai/gascoigne-sdk/go/gascoigne"
)

// Prompt is what every demo asks.
const Prompt = "Call the search_logs tool once, then tell me in one sentence what went wrong " +
	"and for how long."

const (
	infoLine  = "2026-10-13T12:%02d:%02dZ INFO worker-%d handled request id=%d status=200 took=%dms"
	errorLine = "2026-10-13T12:04:10Z ERROR db connection timeout after 30s (pool exhausted)"
)

// Config is the OpenRouter connection.
type Config struct{ Model, APIKey, BaseURL string }

func init() {
	loadDotenv()
	// A dedicated gascoigne server whose LLM proxy forwards to OpenRouter (see gascoigne.yaml).
	if _, file, _, ok := runtime.Caller(0); ok {
		config := filepath.Join(filepath.Dir(file), "..", "..", "gascoigne.yaml")
		setDefaultEnv("GASCOIGNE_CONFIG", config)
	}
	setDefaultEnv("GASCOIGNE_SERVER_ADDR", "127.0.0.1:7879")
}

func setDefaultEnv(key, value string) {
	if os.Getenv(key) == "" {
		_ = os.Setenv(key, value)
	}
}

// loadDotenv reads the nearest .env, walking up from the working directory; real env wins.
func loadDotenv() {
	dir, _ := os.Getwd()
	for {
		if f, err := os.Open(filepath.Join(dir, ".env")); err == nil {
			defer func() { _ = f.Close() }()
			sc := bufio.NewScanner(f)
			for sc.Scan() {
				line := strings.TrimSpace(sc.Text())
				k, v, ok := strings.Cut(line, "=")
				if line == "" || strings.HasPrefix(line, "#") || !ok {
					continue
				}
				if k = strings.TrimSpace(k); os.Getenv(k) == "" {
					_ = os.Setenv(k, strings.Trim(strings.TrimSpace(v), `"'`))
				}
			}
			return
		}
		if parent := filepath.Dir(dir); parent != dir {
			dir = parent
		} else {
			return
		}
	}
}

// Dry reports a run without LLM calls.
func Dry() bool { return os.Getenv("GASCOIGNE_DEMO_DRY") == "1" }

// OpenRouter returns the connection settings, exiting with a hint when the key is missing.
func OpenRouter() Config {
	c := Config{
		Model:   "openai/gpt-4o-mini",
		APIKey:  os.Getenv("OPENROUTER_API_KEY"),
		BaseURL: "https://openrouter.ai/api/v1",
	}
	if m := os.Getenv("OPENROUTER_MODEL"); m != "" {
		c.Model = m
	}
	if c.APIKey == "" {
		if !Dry() {
			fmt.Fprintln(os.Stderr, "OPENROUTER_API_KEY is not set: copy .env.example to .env")
			os.Exit(1)
		}
		c.APIKey = "dry-run"
	}
	return c
}

// SearchLogs is the noisy tool: 400 near-identical lines and one error.
func SearchLogs() string {
	// Request ids differ per run, as in real logs; the proxy caches identical results.
	firstID := int(time.Now().Unix() % 1_000_000)
	lines := make([]string, 0, 401)
	for i := range 400 {
		if i == 250 {
			lines = append(lines, errorLine)
		}
		lines = append(lines, fmt.Sprintf(infoLine, i/60, i%60, i%7, firstID+i, i%90))
	}
	return strings.Join(lines, "\n")
}

// Observe returns an OnResult hook that remembers the last call for Report.
func Observe(before *string, res *gascoigne.Result) func(string, gascoigne.Result) {
	return func(b string, r gascoigne.Result) { *before, *res = b, r }
}

// Report prints the answer (if any) and what gascoigne saved.
func Report(rt *gascoigne.Runtime, before string, res gascoigne.Result, answer string) {
	if answer != "" {
		fmt.Printf("Model answer:\n%s\n\n", indent(answer))
	}
	if res.Text == "" {
		fmt.Println("No optimization happened. Is the gascoigne CLI on PATH?")
		fmt.Println("Install: mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne")
		return
	}
	fmt.Printf("Tool result: %d tokens\n%s\n\n", res.RawTokens, preview(before))
	fmt.Printf("Model reads: %d tokens\n%s\n\n", res.OutTokens, preview(res.Text))
	raw, out := rt.Stats()
	fmt.Printf("Saved %.0f%%: %d -> %d tokens.\n", 100*(1-float64(out)/float64(raw)), raw, out)
	fmt.Printf("Original: gascoigne raw %s\n", res.RawID)
}

// preview is the first lines of a text, each cut to the display width.
func preview(s string) string {
	const lines, width = 8, 72
	rows := strings.Split(s, "\n")
	shown := rows[:min(len(rows), lines)]
	if len(rows) > lines {
		shown = append(shown, fmt.Sprintf("... %d more lines", len(rows)-lines))
	}
	for i, row := range shown {
		shown[i] = row[:min(len(row), width)]
	}
	return indent(strings.Join(shown, "\n"))
}

func indent(s string) string {
	return "  " + strings.ReplaceAll(strings.TrimSpace(s), "\n", "\n  ")
}

// proxyEvent is one run recorded by the gascoigne server, as GET /api/events lists it.
type proxyEvent struct {
	ID        int    `json:"id"`
	Pipeline  string `json:"pipeline"`
	Route     string `json:"route"`
	Command   string `json:"command"`
	RawTokens int    `json:"raw_tokens"`
	OutTokens int    `json:"out_tokens"`
	RawID     string `json:"raw_id"`
}

// proxyEvents lists the proxy events recorded after id, oldest first.
func proxyEvents(after int) []proxyEvent {
	addr := os.Getenv("GASCOIGNE_SERVER_ADDR")
	url := fmt.Sprintf("http://%s/api/events?after=%d&limit=200", addr, after)
	resp, err := http.Get(url)
	if err != nil {
		return nil
	}
	defer func() { _ = resp.Body.Close() }()
	var all []proxyEvent
	if json.NewDecoder(resp.Body).Decode(&all) != nil {
		return nil
	}
	events := slices.DeleteFunc(all, func(e proxyEvent) bool { return e.Pipeline != "proxy" })
	slices.SortFunc(events, func(a, b proxyEvent) int { return a.ID - b.ID })
	return events
}

// ProxyMark is the id of the newest proxy event; pass it to ReportProxy after the agent ran.
func ProxyMark() int {
	events := proxyEvents(0)
	if len(events) == 0 {
		return 0
	}
	return events[len(events)-1].ID
}

// ReportProxy prints the answer and the tool results the proxy shortened since mark.
func ReportProxy(mark int, answer string) {
	fmt.Printf("Model answer:\n%s\n\n", indent(answer))
	var results []proxyEvent
	for range 10 {
		results = slices.DeleteFunc(proxyEvents(mark), func(e proxyEvent) bool {
			return e.RawTokens == 0 || e.Route != "default"
		})
		if len(results) > 0 {
			break
		}
		time.Sleep(200 * time.Millisecond)
	}
	if len(results) == 0 {
		fmt.Println("The proxy saw no new tool result. Is the gascoigne CLI on PATH?")
		return
	}
	fmt.Println("Tool results shortened by the proxy:")
	for _, e := range results {
		saved := 100 * (1 - float64(e.OutTokens)/float64(e.RawTokens))
		fmt.Printf("  %s: %d -> %d tokens (saved %.0f%%)\n",
			e.Command, e.RawTokens, e.OutTokens, saved)
		fmt.Printf("  Original: gascoigne raw %s\n", e.RawID)
	}
}
