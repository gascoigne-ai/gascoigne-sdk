// langchaingo demo: a one-shot agent reads a noisy log through a gascoigne-wrapped tool.
//
//	export OPENROUTER_API_KEY=sk-or-...
//	go run ./langchaingo                       # real run
//	GASCOIGNE_DEMO_DRY=1 go run ./langchaingo  # no LLM call
package main

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/gascoigne-ai/gascoigne-sdk/go/gascoigne"
	"github.com/tmc/langchaingo/agents"
	"github.com/tmc/langchaingo/chains"
	"github.com/tmc/langchaingo/llms/openai"
	"github.com/tmc/langchaingo/tools"
)

const (
	baseURL = "https://openrouter.ai/api/v1"
	prompt  = "Call the search_logs tool once, then tell me in one sentence what went wrong and for how long."
)

type searchLogs struct{}

func (searchLogs) Name() string        { return "search_logs" }
func (searchLogs) Description() string { return "Return the recent service logs. Input is ignored." }
func (searchLogs) Call(context.Context, string) (string, error) {
	lines := make([]string, 0, 401)
	for i := range 400 {
		if i == 250 {
			lines = append(lines, "2026-10-13T12:04:10Z ERROR db connection timeout after 30s (pool exhausted)")
		}
		lines = append(lines, fmt.Sprintf("2026-10-13T12:%02d:%02dZ INFO worker-%d handled request id=%d status=200 took=%dms",
			i/60, i%60, i%7, i, i%90))
	}
	return strings.Join(lines, "\n"), nil
}

func main() {
	ctx := context.Background()
	model := getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
	var before string
	var res gascoigne.Result
	rt := gascoigne.New(gascoigne.Options{
		Agent:    "langchaingo",
		OnResult: func(b string, r gascoigne.Result) { before, res = b, r },
	})
	fmt.Printf("🌘 gascoigne · agents read less, nothing gets lost\n   langchaingo → OpenRouter (%s)\n\n", model)

	tool := rt.WrapTool(searchLogs{})
	if os.Getenv("GASCOIGNE_DEMO_DRY") == "1" {
		fmt.Println("dry run: no LLM call, only the tool")
		tool.Call(ctx, "")
		report(rt, before, res, "")
		return
	}
	key := os.Getenv("OPENROUTER_API_KEY")
	if key == "" {
		fmt.Fprintln(os.Stderr, "OPENROUTER_API_KEY is not set (https://openrouter.ai/keys)")
		os.Exit(1)
	}
	llm, err := openai.New(openai.WithBaseURL(baseURL), openai.WithToken(key), openai.WithModel(model))
	if err != nil {
		panic(err)
	}
	// langchaingo's tools.Tool has the same method set as gascoigne.Tool.
	agent := agents.NewOneShotAgent(llm, []tools.Tool{tool}, agents.WithMaxIterations(4))
	answer, err := chains.Run(ctx, agents.NewExecutor(agent), prompt)
	if err != nil {
		panic(err)
	}
	report(rt, before, res, answer)
}

func getenv(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func report(rt *gascoigne.Runtime, before string, res gascoigne.Result, answer string) {
	if answer != "" {
		fmt.Printf("🤖 %s\n\n", strings.TrimSpace(answer))
	}
	if res.Text == "" {
		fmt.Println("bypassed: is the gascoigne CLI on PATH?  mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne")
		return
	}
	fmt.Printf("🐘 tool result · %d tokens\n%s\n\n🌘 model reads · %d tokens\n%s\n\n",
		res.RawTokens, preview(before), res.OutTokens, preview(res.Text))
	raw, out := rt.Stats()
	saved := 1 - float64(out)/float64(raw)
	n := int(saved * 30)
	fmt.Printf("📉 savings \x1b[32m%s\x1b[31m%s\x1b[0m %.0f%%  %d → %d tokens  (original: gascoigne raw %s)\n",
		strings.Repeat("█", n), strings.Repeat("░", 30-n), saved*100, raw, out, res.RawID)
}

func preview(s string) string {
	lines := strings.Split(s, "\n")
	if len(lines) > 8 {
		lines = append(lines[:8], fmt.Sprintf("… %d more lines", len(lines)-8))
	}
	for i, l := range lines {
		lines[i] = "  │ " + l[:min(len(l), 72)]
	}
	return strings.Join(lines, "\n")
}
