package gascoigne

import "context"

// Tool is the shape shared by langchaingo's tools.Tool and many other Go agent frameworks.
type Tool interface {
	Name() string
	Description() string
	Call(ctx context.Context, input string) (string, error)
}

type wrapped struct {
	Tool
	rt *Runtime
}

func (w wrapped) Call(ctx context.Context, input string) (string, error) {
	out, err := w.Tool.Call(ctx, input)
	if err != nil {
		return out, err
	}
	return w.rt.Optimize(ctx, out, Attrs{Tool: w.Name()}), nil
}

// WrapTool optimizes what t returns. It satisfies the same interface as t.
func (r *Runtime) WrapTool(t Tool) Tool { return wrapped{t, r} }

// Fn is a tool function taking a typed input and returning text.
type Fn[In any] func(context.Context, In) (string, error)

// WrapFunc optimizes the string a tool function returns; errors pass through.
func WrapFunc[In any](r *Runtime, name string, fn Fn[In]) Fn[In] {
	return func(ctx context.Context, in In) (string, error) {
		out, err := fn(ctx, in)
		if err != nil {
			return out, err
		}
		return r.Optimize(ctx, out, Attrs{Tool: name}), nil
	}
}
