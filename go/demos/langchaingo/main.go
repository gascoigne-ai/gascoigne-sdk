// langchaingo + OpenRouter. Two added lines (marked).
package main

import (
	"context"

	"github.com/gascoigne-ai/gascoigne-sdk/go/demos/kit"
	"github.com/gascoigne-ai/gascoigne-sdk/go/gascoigne"
	"github.com/tmc/langchaingo/agents"
	"github.com/tmc/langchaingo/chains"
	"github.com/tmc/langchaingo/llms/openai"
	"github.com/tmc/langchaingo/tools"
)

type searchLogs struct{}

func (searchLogs) Name() string        { return "search_logs" }
func (searchLogs) Description() string { return "Return the recent service logs. Input is ignored." }
func (searchLogs) Call(context.Context, string) (string, error) {
	return kit.SearchLogs(), nil
}

func main() {
	ctx := context.Background()
	var before string
	var res gascoigne.Result
	rt := gascoigne.New(gascoigne.Options{Agent: "langchaingo", OnResult: kit.Observe(&before, &res)}) // 1. start gascoigne
	logs := rt.WrapTool(searchLogs{})                                                                  // 2. wrap the tool

	if kit.Dry() {
		_, _ = logs.Call(ctx, "")
		kit.Report(rt, before, res, "")
		return
	}
	cfg := kit.OpenRouter()
	llm, err := openai.New(openai.WithBaseURL(cfg.BaseURL), openai.WithToken(cfg.APIKey), openai.WithModel(cfg.Model))
	if err != nil {
		panic(err)
	}
	agent := agents.NewOneShotAgent(llm, []tools.Tool{logs}, agents.WithMaxIterations(4))
	answer, err := chains.Run(ctx, agents.NewExecutor(agent), kit.Prompt)
	if err != nil {
		panic(err)
	}
	kit.Report(rt, before, res, answer)
}
