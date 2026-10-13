// langchaingo through the gascoigne proxy: the tool is not wrapped. One added line.
package main

import (
	"cmp"
	"context"
	"fmt"

	"github.com/gascoigne-ai/gascoigne-sdk/go/demos/kit"
	"github.com/gascoigne-ai/gascoigne-sdk/go/gascoigne"
	"github.com/tmc/langchaingo/agents"
	"github.com/tmc/langchaingo/chains"
	"github.com/tmc/langchaingo/llms/openai"
	"github.com/tmc/langchaingo/tools"
)

// searchLogs is a plain tool with no gascoigne code in it.
type searchLogs struct{}

func (searchLogs) Name() string        { return "search_logs" }
func (searchLogs) Description() string { return "Return the recent service logs." }
func (searchLogs) Call(context.Context, string) (string, error) {
	return kit.SearchLogs(), nil
}

func main() {
	ctx := context.Background()
	cfg := kit.OpenRouter()
	if kit.Dry() {
		fmt.Println("Dry run: the proxy rewrites LLM requests, nothing to show.")
		return
	}

	// 1. Start gascoigne.
	rt := gascoigne.New(gascoigne.Options{Agent: "langchaingo"})

	// 2. Send LLM traffic through the gascoigne proxy.
	baseURL := cmp.Or(rt.ProxyBaseURL(ctx, "openai"), cfg.BaseURL)

	llm, err := openai.New(
		openai.WithBaseURL(baseURL),
		openai.WithToken(cfg.APIKey),
		openai.WithModel(cfg.Model),
	)
	if err != nil {
		panic(err)
	}
	mark := kit.ProxyMark()
	agent := agents.NewOneShotAgent(llm, []tools.Tool{searchLogs{}}, agents.WithMaxIterations(4))
	answer, err := chains.Run(ctx, agents.NewExecutor(agent), kit.Prompt)
	if err != nil {
		panic(err)
	}
	kit.ReportProxy(mark, answer)
}
