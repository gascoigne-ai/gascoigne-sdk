/** Vercel AI SDK helper: optimize what `tool({ execute })` results hand to the model. */
import { type Runtime, runtime } from "@gascoigne/sdk";

interface ToolLike {
  execute?: (...args: any[]) => unknown;
}

/**
 * Wrap `execute` of every tool in a `tools` record; tools without `execute` pass through.
 * String results are optimized, other results are returned as they are.
 */
export function wrapTools<T extends Record<string, ToolLike>>(
  tools: T,
  rt: Runtime = runtime(),
): T {
  const out: Record<string, ToolLike> = {};
  for (const [name, t] of Object.entries(tools)) {
    const exec = t.execute;
    out[name] = exec
      ? Object.assign(Object.create(Object.getPrototypeOf(t)), t, {
          execute: async (...args: unknown[]) => {
            const r = await exec.apply(t, args);
            return typeof r === "string" ? rt.optimize(r, { tool: name }) : r;
          },
        })
      : t;
  }
  return out as T;
}
