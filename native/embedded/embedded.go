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
func New(ctx context.Context, options Options) (gascoigne.Backend, error) {
	eng, err := inproc.New(ctx, options)
	if err != nil {
		return nil, err
	}
	return backend{eng: eng}, nil
}

func (b backend) Optimize(
	ctx context.Context, request gascoigne.Request,
) (gascoigne.Result, error) {
	res, err := b.eng.Optimize(ctx, inproc.Request{
		Text: request.Text, Tool: request.Attrs.Tool, Cmd: request.Attrs.Cmd,
		URL: request.Attrs.URL, Query: request.Attrs.Query, Session: request.Session,
		Agent: request.Agent, Model: request.Attrs.Model,
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

// Totals and Runs make the backend a gascoigne.LedgerBackend. The engine's types carry
// the same fields as the SDK's, so they convert directly.

func (b backend) Totals(
	ctx context.Context, query gascoigne.TotalsQuery,
) ([]gascoigne.Total, error) {
	rows, err := b.eng.Stats(ctx, inproc.StatsQuery{
		By: query.By, Session: query.Session, Agent: query.Agent, Model: query.Model,
		Since: query.Since,
	})
	out := make([]gascoigne.Total, len(rows))
	for i, row := range rows {
		out[i] = gascoigne.Total(row)
	}
	return out, err
}

func (b backend) Runs(ctx context.Context, query gascoigne.RunsQuery) ([]gascoigne.Run, error) {
	rows, err := b.eng.Recent(ctx, inproc.RecentQuery{
		Session: query.Session, Agent: query.Agent, Model: query.Model, Since: query.Since,
		Before: query.Before, Limit: query.Limit,
	})
	out := make([]gascoigne.Run, len(rows))
	for i, row := range rows {
		out[i] = gascoigne.Run(row)
	}
	return out, err
}

var _ gascoigne.LedgerBackend = backend{}

func (b backend) Close() error { return b.eng.Close(context.Background()) }
