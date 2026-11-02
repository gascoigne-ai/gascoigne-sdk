// Package embedded runs the gascoigne engine inside a Go program, as a gascoigne.Backend. Use it
// with the Go SDK when the process should need no server and no CLI:
//
//	b, err := embedded.New(ctx, embedded.Options{Set: []string{"optimizers.grep.max_per_file=50"}})
//	rt := gascoigne.New(gascoigne.Options{Backend: b})
//
// Configuration is merged by the engine: defaults, the user's file, Options.Config, then the
// Set/Only/Disable lists.
package embedded

import (
	"context"

	"github.com/gascoigne-ai/gascoigne-cli/inproc"
	"github.com/gascoigne-ai/gascoigne-sdk/go/gascoigne"
)

// Options are the engine's configuration layers; see inproc.Options.
type Options = inproc.Options

type backend struct{ eng *inproc.Engine }

// New starts an engine and returns it as a Backend.
func New(ctx context.Context, o Options) (gascoigne.Backend, error) {
	eng, err := inproc.New(ctx, o)
	if err != nil {
		return nil, err
	}
	return backend{eng: eng}, nil
}

func (b backend) Optimize(ctx context.Context, r gascoigne.Request) (gascoigne.Result, error) {
	res, err := b.eng.Optimize(ctx, inproc.Request{
		Text: r.Text, Tool: r.Attrs.Tool, Cmd: r.Attrs.Cmd, URL: r.Attrs.URL,
		Query: r.Attrs.Query, Session: r.Session, Agent: r.Agent, Model: r.Attrs.Model,
	})
	if err != nil {
		return gascoigne.Result{}, err
	}
	return gascoigne.Result{
		Text: res.Text, RawID: res.RawID, RawTokens: res.RawTokens,
		OutTokens: res.OutTokens, Skipped: res.Skipped,
	}, nil
}

func (b backend) Raw(ctx context.Context, id string) (string, error) { return b.eng.Raw(ctx, id) }

func (b backend) Close() error { return b.eng.Close(context.Background()) }
