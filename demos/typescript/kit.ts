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
function loadOpenRouter() {
  const apiKey = process.env.OPENROUTER_API_KEY ?? (dry ? "dry-run" : "");
  if (!apiKey) {
    console.error("OPENROUTER_API_KEY is not set: copy .env.example to .env");
    process.exit(1);
  }
  return { model: MODEL, apiKey, baseURL: "https://openrouter.ai/api/v1" };
}

export const openrouter = loadOpenRouter();

// A dedicated gascoigne server whose LLM proxy forwards to OpenRouter (see gascoigne.yaml).
process.env.GASCOIGNE_CONFIG ??= resolve(import.meta.dirname, "..", "gascoigne.yaml");
process.env.GASCOIGNE_SERVER_ADDR ??= "127.0.0.1:7879";

export function searchLogs(): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  // Request ids differ per call, as in real logs; the proxy caches identical results.
  const firstId = Math.floor(Math.random() * 900_000);
  const lines = Array.from({ length: 400 }, (_, i) => {
    const time = `12:${pad(Math.floor(i / 60))}:${pad(i % 60)}`;
    const id = firstId + i;
    return `2026-10-13T${time}Z INFO worker-${i % 7} handled request id=${id} took=${i % 90}ms`;
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

interface ProxyEvent {
  id: number;
  pipeline: string;
  route: string;
  command: string;
  raw_tokens: number;
  out_tokens: number;
  raw_id: string;
}

/** Events the gascoigne server recorded after id `after`, oldest first. */
async function proxyEvents(after = 0): Promise<ProxyEvent[]> {
  try {
    const url = `http://${process.env.GASCOIGNE_SERVER_ADDR}/api/events?after=${after}&limit=200`;
    const events = (await (await fetch(url)).json()) as ProxyEvent[];
    return events.filter((e) => e.pipeline === "proxy").sort((a, b) => a.id - b.id);
  } catch {
    return [];
  }
}

/** Tool-result events after id `after`; the server records them just after answering. */
async function awaitResults(after: number): Promise<ProxyEvent[]> {
  for (let attempt = 0; attempt < 10; attempt++) {
    const results = (await proxyEvents(after)).filter((e) => e.raw_tokens && e.route === "default");
    if (results.length) return results;
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  return [];
}

/** Run the agent, then list the tool results the gascoigne proxy shortened on the way. */
export async function runProxy(ask: () => Promise<unknown>): Promise<void> {
  console.log(`gascoigne proxy demo: ${sdk().agent} via OpenRouter (${MODEL})\n`);
  if (dry) {
    console.log(
      "Dry run: the proxy rewrites LLM requests, so there is nothing to show without one.",
    );
    return;
  }
  const seen = (await proxyEvents()).at(-1)?.id ?? 0;
  console.log(`Model answer:\n${preview(String(await ask()), 20)}\n`);
  const results = await awaitResults(seen);
  if (!results.length) {
    console.log("The proxy saw no new tool result. Is the gascoigne CLI on PATH?");
    return;
  }
  console.log("Tool results shortened by the proxy:");
  for (const e of results) {
    const saved = Math.round((1 - e.out_tokens / e.raw_tokens) * 100);
    console.log(
      `  ${e.command || "tool result"}: ${count(e.raw_tokens)} -> ${count(e.out_tokens)} tokens` +
        ` (saved ${saved}%)`,
    );
    console.log(`  Original: gascoigne raw ${e.raw_id}`);
  }
}
