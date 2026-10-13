/**
 * Everything a demo needs that is NOT about integrating gascoigne: env, OpenRouter, the noisy tool,
 * the report. Read the other files, not this one.
 */
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { type Result, runtime as sdk, stats } from "@gascoigne/sdk";

// Load the nearest .env, walking up from the working directory.
for (let dir = resolve("."); ; dir = dirname(dir)) {
  if (existsSync(join(dir, ".env"))) {
    process.loadEnvFile(join(dir, ".env"));
    break;
  }
  if (dirname(dir) === dir) break;
}

export const PROMPT =
  "Call the search_logs tool once, then tell me in one sentence what went wrong and for how long.";
export const dry = process.env.GASCOIGNE_DEMO_DRY === "1";
export const MODEL = process.env.OPENROUTER_MODEL ?? "openai/gpt-4o-mini";

/** OpenRouter settings; exits with a hint when the key is missing (except in a dry run). */
export function openrouter() {
  const apiKey = process.env.OPENROUTER_API_KEY ?? (dry ? "dry-run" : "");
  if (!apiKey) {
    console.error("OPENROUTER_API_KEY is not set: copy .env.example to .env");
    process.exit(1);
  }
  return { model: MODEL, apiKey, baseURL: "https://openrouter.ai/api/v1" };
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

const c = (code: number, s: string) => (process.stdout.isTTY ? `\x1b[${code}m${s}\x1b[0m` : s);
const W = 52;
const seen: { before: string; res: Result }[] = [];

function box(title: string, body: string[], color: number): string {
  const rows = body.map((l) => `│ ${l.slice(0, W - 2).padEnd(W - 2)} │`);
  const top = `╭─ ${title} ${"─".repeat(Math.max(0, W - title.length - 4))}╮`;
  return [top, ...rows, `╰${"─".repeat(W)}╯`].map((l) => c(color, l)).join("\n");
}

function preview(text: string, n = 8): string[] {
  const lines = text.split("\n");
  return [...lines.slice(0, n), ...(lines.length > n ? [`… ${lines.length - n} more lines`] : [])];
}

/** Run the agent (`ask`), or just the tool in a dry run, then print what gascoigne saved. */
export async function run(ask: () => Promise<unknown>, tool: () => unknown): Promise<void> {
  const rt = sdk();
  rt.setOnResult((before, res) => seen.push({ before, res }));
  console.log(c(36, `🌘 gascoigne  ${rt.agent} → OpenRouter (${MODEL})`));
  let answer = "";
  if (dry) {
    console.log(c(2, "dry run: no LLM call, only the tool"));
    await tool();
  } else {
    answer = String(await ask());
  }
  if (answer) console.log(box("🤖 model answer", answer.trim().split("\n"), 32));
  const last = seen.at(-1);
  if (!last) {
    console.log(
      c(
        33,
        "bypassed: is the gascoigne CLI on PATH?  mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne",
      ),
    );
    return;
  }
  console.log(box(`🐘 tool result · ${last.res.rawTokens} tokens`, preview(last.before), 31));
  console.log(box(`🌘 model reads · ${last.res.outTokens} tokens`, preview(last.res.text), 32));
  const { rawTokens: raw, outTokens: out } = stats();
  const saved = raw ? 1 - out / raw : 0;
  const filled = Math.round(saved * 30);
  console.log(
    c(36, "📉 savings ") +
      c(32, "█".repeat(filled)) +
      c(31, "░".repeat(30 - filled)) +
      c(1, ` ${Math.round(saved * 100)}%`) +
      `  ${raw.toLocaleString()} → ${out.toLocaleString()} tokens` +
      c(2, `  original: gascoigne raw ${last.res.rawId}`),
  );
}
