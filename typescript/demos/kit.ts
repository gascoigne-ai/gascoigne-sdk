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
  const pad = (n: number) => String(n).padStart(2, "0");
  const lines = Array.from({ length: 400 }, (_, i) => {
    const time = `12:${pad(Math.floor(i / 60))}:${pad(i % 60)}`;
    return `2026-10-13T${time}Z INFO worker-${i % 7} handled request id=${i} took=${i % 90}ms`;
  });
  lines.splice(
    250,
    0,
    "2026-10-13T12:04:10Z ERROR db connection timeout after 30s (pool exhausted)",
  );
  return lines.join("\n");
}

const WIDTH = 72;
const count = (n: number) => n.toLocaleString();
const seen: { before: string; result: Result }[] = [];

/** The first lines of a text, each cut to the display width. */
function preview(text: string, lines = 8): string {
  const rows = text.split("\n");
  const shown = rows.slice(0, lines);
  if (rows.length > lines) shown.push(`... ${rows.length - lines} more lines`);
  return shown.map((row) => `  ${row.slice(0, WIDTH)}`).join("\n");
}

/** Run the agent (`ask`), or just the tool in a dry run, then print what gascoigne saved. */
export async function run(ask: () => Promise<unknown>, tool: () => unknown): Promise<void> {
  const runtime = sdk();
  runtime.setOnResult((before, result) => seen.push({ before, result }));
  console.log(`gascoigne demo: ${runtime.agent} via OpenRouter (${MODEL})\n`);
  let answer = "";
  if (dry) {
    console.log("Dry run: no LLM call, only the tool.\n");
    await tool();
  } else {
    answer = String(await ask());
  }
  if (answer) console.log(`Model answer:\n${preview(answer, 20)}\n`);
  const last = seen.at(-1);
  if (!last) {
    console.log("No optimization happened. Is the gascoigne CLI on PATH?");
    console.log("Install: mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne");
    return;
  }
  const { result } = last;
  console.log(`Tool result: ${count(result.rawTokens)} tokens\n${preview(last.before)}\n`);
  console.log(`Model reads: ${count(result.outTokens)} tokens\n${preview(result.text)}\n`);
  const { rawTokens, outTokens } = stats();
  const saved = rawTokens ? Math.round((1 - outTokens / rawTokens) * 100) : 0;
  console.log(`Saved ${saved}%: ${count(rawTokens)} -> ${count(outTokens)} tokens.`);
  console.log(`Original: gascoigne raw ${last.result.rawId}`);
}
