/**
 * Shared bits of the demos: OpenRouter settings, a noisy tool, and a before/after report.
 *
 *   export OPENROUTER_API_KEY=sk-or-...         # required for real runs
 *   export OPENROUTER_MODEL=openai/gpt-4o-mini  # optional
 *   pnpm --filter gascoigne-ts-demos ai-sdk
 *   GASCOIGNE_DEMO_DRY=1 pnpm --filter gascoigne-ts-demos ai-sdk   # no LLM call
 */
import { init, stats, type Result, type Runtime } from "@gascoigne/sdk";

export const BASE_URL = "https://openrouter.ai/api/v1";
export const MODEL = process.env.OPENROUTER_MODEL ?? "openai/gpt-4o-mini";
export const PROMPT =
  "Call the search_logs tool once, then tell me in one sentence what went wrong and for how long.";
export const dry = () => process.env.GASCOIGNE_DEMO_DRY === "1";

const c = (code: number, s: string) => (process.stdout.isTTY ? `\x1b[${code}m${s}\x1b[0m` : s);
const W = 52;
const seen: { before: string; res: Result }[] = [];

export function apiKey(): string {
  const key = process.env.OPENROUTER_API_KEY;
  if (!key && !dry()) {
    console.error(c(31, "OPENROUTER_API_KEY is not set") + " (https://openrouter.ai/keys)");
    process.exit(1);
  }
  return key ?? "dry-run";
}

export function searchLogs(): string {
  const lines = Array.from(
    { length: 400 },
    (_, i) =>
      `2026-10-13T12:${String(Math.floor(i / 60)).padStart(2, "0")}:${String(i % 60).padStart(2, "0")}Z ` +
      `INFO worker-${i % 7} handled request id=${i} status=200 took=${i % 90}ms`,
  );
  lines.splice(250, 0, "2026-10-13T12:04:10Z ERROR db connection timeout after 30s (pool exhausted)");
  return lines.join("\n");
}

function box(title: string, body: string[], color: number): string[] {
  const top = `╭─ ${title} ${"─".repeat(Math.max(0, W - title.length - 4))}╮`;
  const rows = body.map((l) => `│ ${l.slice(0, W - 2).padEnd(W - 2)} │`);
  return [c(color, top), ...rows.map((r) => c(color, r)), c(color, `╰${"─".repeat(W)}╯`)];
}

function preview(text: string, n = 8): string[] {
  const lines = text.split("\n");
  return [...lines.slice(0, n), ...(lines.length > n ? [`… ${lines.length - n} more lines`] : [])];
}

export function runtime(framework: string): Runtime {
  console.log(
    box("🌘 gascoigne · agents read less, nothing gets lost", [`${framework} → OpenRouter (${MODEL})`], 36).join("\n"),
  );
  return init({ agent: framework, onResult: (before, res) => seen.push({ before, res }) });
}

export function report(answer?: string): void {
  if (answer) console.log(box("🤖 model answer", answer.trim().split("\n"), 32).join("\n"));
  const last = seen.at(-1);
  if (!last) {
    console.log(c(33, "bypassed: is the gascoigne CLI on PATH?  mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne"));
    return;
  }
  console.log(box(`🐘 tool result · ${last.res.rawTokens} tokens`, preview(last.before), 31).join("\n"));
  console.log(box(`🌘 model reads · ${last.res.outTokens} tokens`, preview(last.res.text), 32).join("\n"));
  const { rawTokens: raw, outTokens: out } = stats();
  const saved = raw ? 1 - out / raw : 0;
  const filled = Math.round(saved * 30);
  console.log(
    c(36, "📉 savings ") +
      c(32, "█".repeat(filled)) + c(31, "░".repeat(30 - filled)) +
      c(1, ` ${Math.round(saved * 100)}%`) + `  ${raw.toLocaleString()} → ${out.toLocaleString()} tokens` +
      c(2, `  (original: gascoigne raw ${last.res.rawId})`),
  );
}

/** Without an LLM: call the registered tool the way the framework would. */
export async function dryCall(tool: () => unknown): Promise<void> {
  console.log(c(2, "dry run: no LLM call, only the tool"));
  await tool();
  report();
}
