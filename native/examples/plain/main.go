// Native, no LLM needed: the engine runs inside this Go program (no server, no CLI).
//
//	cd native && go run ./examples/plain
package main

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/gascoigne-ai/gascoigne-sdk/go/gascoigne"
	"github.com/gascoigne-ai/gascoigne-sdk/native/embedded"
)

func noisyLog() string {
	var b strings.Builder
	for i := 0; i < 400; i++ {
		fmt.Fprintf(&b, "2026-10-13T12:%02d:%02dZ INFO worker-%d handled request id=%d\n",
			i/60, i%60, i%7, i)
		if i == 250 {
			b.WriteString("2026-10-13T12:04:10Z ERROR db connection timeout after 30s\n")
		}
	}
	return b.String()
}

func main() {
	ctx := context.Background()
	// 1. Start gascoigne in native mode. New fails when the engine cannot start.
	backend, err := embedded.New(ctx, embedded.Options{})
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	rt := gascoigne.New(gascoigne.Options{Agent: "go-demo", Backend: backend})
	defer func() { _ = rt.Close() }()

	// 2. Optimize the tool result.
	res := rt.OptimizeResult(ctx, noisyLog(), gascoigne.Attrs{Tool: "search_logs"})

	fmt.Printf("Tool result: %d tokens\nModel reads: %d tokens\n\n", res.RawTokens, res.OutTokens)
	for _, line := range strings.Split(strings.TrimSpace(res.Text), "\n") {
		fmt.Println(" ", line)
	}
	fmt.Printf("\nSaved %d%%. Original: gascoigne raw %s\n",
		100-res.OutTokens*100/max(res.RawTokens, 1), res.RawID)
}
