// Package kit holds everything a demo needs that is not about integrating gascoigne: env,
// OpenRouter settings, the noisy tool, and the report. Read the demos' main.go, not this file.
package kit

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"

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

func init() { loadDotenv() }

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
	lines := make([]string, 0, 401)
	for i := range 400 {
		if i == 250 {
			lines = append(lines, errorLine)
		}
		lines = append(lines, fmt.Sprintf(infoLine, i/60, i%60, i%7, i, i%90))
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
