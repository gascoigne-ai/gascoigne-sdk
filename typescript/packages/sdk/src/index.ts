/**
 * Embed gascoigne token optimization in agent frameworks.
 *
 * Every call is safe: when the gascoigne CLI is missing or the server misbehaves, inputs come back
 * unchanged and nothing is thrown.
 */
import { spawn } from "node:child_process";
import { accessSync, constants } from "node:fs";
import { delimiter, join } from "node:path";

const PROTO = 1;
const DEFAULT_ADDR = "127.0.0.1:7878";
const INSTALL_HINT = "mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne";
const BREAKER_FAILURES = 5;
const BREAKER_PAUSE_MS = 60_000;

export interface Result {
  text: string;
  rawId: string;
  rawTokens: number;
  outTokens: number;
  skipped: string;
}

export interface Attrs {
  tool?: string;
  cmd?: string;
  url?: string;
  query?: string;
  model?: string;
}

/** Body of `POST /sdk/v1/optimize`. */
interface OptimizeRequest extends Attrs {
  text: string;
  agent?: string;
  session?: string;
}

/** Response of `POST /sdk/v1/optimize`. */
interface OptimizeResponse {
  text: string;
  raw_id?: string;
  raw_tokens?: number;
  out_tokens?: number;
  skipped?: string;
}

export interface Stats {
  rawTokens: number;
  outTokens: number;
}

export interface Options {
  agent?: string;
  session?: string;
  /** Per-call timeout, default 5000 ms. */
  timeoutMs?: number;
  /** Called with (original, result) after each optimized call; errors in it are ignored. */
  onResult?: (original: string, result: Result) => void;
  /** Where warnings go, default console.warn. */
  warn?: (msg: string) => void;
}

function findOnPath(name: string): string | undefined {
  for (const dir of (process.env.PATH ?? "").split(delimiter)) {
    if (!dir) continue;
    const p = join(dir, name);
    try {
      accessSync(p, constants.X_OK);
      return p;
    } catch {
      /* next */
    }
  }
  return undefined;
}

function toResult(d: OptimizeResponse): Result {
  if (typeof d.text !== "string") throw new Error("bad response");
  return {
    text: d.text,
    rawId: d.raw_id ?? "",
    rawTokens: d.raw_tokens ?? 0,
    outTokens: d.out_tokens ?? 0,
    skipped: d.skipped ?? "",
  };
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export class Runtime {
  private state: "unknown" | "ready" | "bypass" = "unknown";
  private probing?: Promise<void>;
  private failures = 0;
  private pausedUntil = 0;
  private warned = false;
  private total: Stats = { rawTokens: 0, outTokens: 0 };

  constructor(private readonly opts: Options = {}) {}

  get agent(): string {
    return this.opts.agent ?? "";
  }

  /** Replace the observer called with (original, result) after each optimized call. */
  setOnResult(fn: Options["onResult"]): void {
    this.opts.onResult = fn;
  }

  get addr(): string {
    return process.env.GASCOIGNE_SERVER_ADDR || DEFAULT_ADDR;
  }

  get baseUrl(): string {
    return `http://${this.addr}`;
  }

  private disabled(): boolean {
    return process.env.GASCOIGNE_SDK === "off" || process.env.GASCOIGNE_SERVER === "off";
  }

  private warn(msg: string): void {
    if (this.warned) return;
    this.warned = true;
    (this.opts.warn ?? ((m) => console.warn(`[gascoigne] ${m}`)))(msg);
  }

  private async healthy(): Promise<boolean> {
    try {
      const r = await fetch(`${this.baseUrl}/sdk/v1/health`, { signal: AbortSignal.timeout(500) });
      if (!r.ok) return false;
      const { proto } = (await r.json()) as { proto?: number };
      if (proto !== PROTO) {
        this.warn(`gascoigne server speaks proto ${proto}, SDK ${PROTO}; running without optimization`);
        return false;
      }
      return true;
    } catch {
      return false;
    }
  }

  private async startServer(): Promise<boolean> {
    const exe = process.env.GASCOIGNE_BIN || findOnPath("gascoigne");
    if (!exe) {
      this.warn(`gascoigne-cli not found on PATH; running without optimization. Install: ${INSTALL_HINT}`);
      return false;
    }
    try {
      await new Promise<void>((resolve, reject) => {
        const p = spawn(exe, ["server", "start"], { stdio: "ignore" });
        const t = setTimeout(() => {
          p.kill();
          resolve();
        }, 10_000);
        p.on("error", (e) => {
          clearTimeout(t);
          reject(e);
        });
        p.on("exit", () => {
          clearTimeout(t);
          resolve();
        });
      });
    } catch (e) {
      this.warn(`could not start gascoigne server (${e}); running without optimization`);
      return false;
    }
    for (const end = Date.now() + 3000; Date.now() < end; await sleep(100)) {
      if (await this.healthy()) return true;
    }
    this.warn("gascoigne server did not come up; running without optimization");
    return false;
  }

  /** True when optimize calls will be tried. Probes once, then remembers. */
  async ready(): Promise<boolean> {
    if (this.disabled()) return false;
    if (this.state === "unknown") {
      this.probing ??= (async () => {
        this.state = (await this.healthy()) || (await this.startServer()) ? "ready" : "bypass";
      })();
      await this.probing;
    }
    return this.state === "ready" && Date.now() >= this.pausedUntil;
  }

  private failed(): void {
    if (++this.failures >= BREAKER_FAILURES) {
      this.failures = 0;
      this.pausedUntil = Date.now() + BREAKER_PAUSE_MS;
    }
  }

  async optimizeResult(text: string, attrs: Attrs = {}): Promise<Result> {
    const same: Result = { text, rawId: "", rawTokens: 0, outTokens: 0, skipped: "" };
    if (!text || !(await this.ready())) return same;
    const request: OptimizeRequest = { text, agent: this.opts.agent, session: this.opts.session, ...attrs };
    try {
      const r = await fetch(`${this.baseUrl}/sdk/v1/optimize`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(request), // undefined fields are not serialized
        signal: AbortSignal.timeout(this.opts.timeoutMs ?? 5000),
      });
      if (!r.ok) throw new Error(`status ${r.status}`);
      const out = toResult((await r.json()) as OptimizeResponse);
      this.failures = 0;
      this.total = {
        rawTokens: this.total.rawTokens + out.rawTokens,
        outTokens: this.total.outTokens + (out.outTokens || out.rawTokens),
      };
      this.notify(text, out);
      return out;
    } catch {
      this.failed();
      return same;
    }
  }

  private notify(original: string, result: Result): void {
    try {
      this.opts.onResult?.(original, result);
    } catch {
      /* an observer must never break the host app */
    }
  }

  async optimize(text: string, attrs: Attrs = {}): Promise<string> {
    return (await this.optimizeResult(text, attrs)).text;
  }

  /** The original behind an optimized result; empty when unavailable. */
  async raw(rawId: string): Promise<string> {
    if (!(await this.ready())) return "";
    try {
      const r = await fetch(`${this.baseUrl}/sdk/v1/raw/${encodeURIComponent(rawId)}`, {
        signal: AbortSignal.timeout(this.opts.timeoutMs ?? 5000),
      });
      return r.ok ? await r.text() : "";
    } catch {
      this.failed();
      return "";
    }
  }

  /** Base URL that routes an LLM client through the gascoigne proxy, or undefined in bypass. */
  async proxyBaseUrl(api: "openai" | "anthropic" | "gemini" = "openai"): Promise<string | undefined> {
    if (!(await this.ready())) return undefined;
    return api === "openai" ? `${this.baseUrl}/v1` : this.baseUrl;
  }

  stats(): Stats {
    return this.total;
  }

  /** Wrap a tool function so string results are optimized. */
  wrapTool<A extends unknown[], R>(fn: (...args: A) => R | Promise<R>, name = fn.name || "tool") {
    return async (...args: A): Promise<R | string> => {
      const out = await fn(...args);
      return typeof out === "string" ? this.optimize(out, { tool: name }) : out;
    };
  }
}

let current = new Runtime();

/** Configure the process-wide runtime and return it. */
export function init(opts: Options = {}): Runtime {
  current = new Runtime(opts);
  return current;
}

export const runtime = (): Runtime => current;
export const optimize = (text: string, attrs?: Attrs) => current.optimize(text, attrs);
export const wrapTool = <A extends unknown[], R>(fn: (...a: A) => R | Promise<R>, name?: string) =>
  current.wrapTool(fn, name);
export const raw = (id: string) => current.raw(id);
export const proxyBaseUrl = (api?: "openai" | "anthropic" | "gemini") => current.proxyBaseUrl(api);
export const stats = () => current.stats();
