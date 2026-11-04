/**
 * Embed gascoigne token optimization in agent frameworks.
 *
 * Every call is safe: when the gascoigne CLI is missing or the server misbehaves, inputs come back
 * unchanged and nothing is thrown.
 */
import { spawn } from "node:child_process";
import { accessSync, constants } from "node:fs";
import { delimiter, join } from "node:path";
import { Native, type Settings } from "./native.js";

export { NativeError, type Price, type Pricing, type Settings } from "./native.js";

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

/** The recorded runs of one group, summed. */
export interface Total {
  group: string;
  runs: number;
  optimized: number;
  failed: number;
  rawTokens: number;
  outTokens: number;
  saved: number;
  /** RFC 3339, empty when unknown. */
  first: string;
  last: string;
}

/** One recorded optimization. */
export interface Run {
  id: number;
  /** RFC 3339. */
  time: string;
  session: string;
  agent: string;
  model: string;
  command: string;
  route: string;
  optimizers: string[];
  rawTokens: number;
  outTokens: number;
  durationNs: number;
  rawId: string;
  outcome: string;
  reason: string;
}

/** The tokens saved, priced for one model. `source` is built-in, static, json, api or script. */
export interface ModelCost {
  model: string;
  source: string;
  assumed: boolean;
  tokenizer: string;
  tokens: number;
  modelTokens: number;
  firstReadUsd: number;
  inContextUsd: number;
}

/**
 * What the tokens saved are worth: an estimate from list prices or the prices configured for
 * gascoigne, not what anyone is billed. With `billing === "subscription"` there are no dollars.
 */
export interface Costs {
  billing: string;
  firstReadUsd: number;
  inContextUsd: number;
  rereads: number;
  savings: ModelCost[];
  unpriced: string[];
}

/** Filters for `totals` and `costs`; empty ones match everything. `by` is route (default),
 * session, family, optimizer, command, outcome, agent, model, day, week or month (totals only). */
export interface TotalsQuery {
  by?: string;
  session?: string;
  agent?: string;
  model?: string;
  since?: Date;
}

/**
 * Filters for `runs`, newest first. `before` is a run id, to page; `limit` defaults to 50, at
 * most 1000.
 */
export interface RunsQuery {
  session?: string;
  agent?: string;
  model?: string;
  since?: Date;
  before?: number;
  limit?: number;
}

type Wire = Record<string, unknown>;

const str = (v: unknown): string => (typeof v === "string" ? v : "");
const num = (v: unknown): number => (typeof v === "number" ? v : 0);
const list = (v: unknown): Wire[] => (Array.isArray(v) ? (v as Wire[]) : []);

const toTotal = (d: Wire): Total => ({
  group: str(d.group),
  runs: num(d.runs),
  optimized: num(d.optimized),
  failed: num(d.failed),
  rawTokens: num(d.raw_tokens),
  outTokens: num(d.out_tokens),
  saved: num(d.saved),
  first: str(d.first),
  last: str(d.last),
});

const toRun = (d: Wire): Run => ({
  id: num(d.id),
  time: str(d.time),
  session: str(d.session),
  agent: str(d.agent),
  model: str(d.model),
  command: str(d.command),
  route: str(d.route),
  optimizers: list(d.optimizers).map(String),
  rawTokens: num(d.raw_tokens),
  outTokens: num(d.out_tokens),
  durationNs: num(d.duration_ns),
  rawId: str(d.raw_id),
  outcome: str(d.outcome),
  reason: str(d.reason),
});

const toModelCost = (d: Wire): ModelCost => ({
  model: str(d.model),
  source: str(d.source),
  assumed: d.assumed === true,
  tokenizer: str(d.tokenizer),
  tokens: num(d.tokens),
  modelTokens: num(d.model_tokens),
  firstReadUsd: num(d.first_read_usd),
  inContextUsd: num(d.in_context_usd),
});

const toCosts = (d: Wire): Costs => ({
  billing: str(d.billing),
  firstReadUsd: num(d.first_read_usd),
  inContextUsd: num(d.in_context_usd),
  rereads: num(d.rereads),
  savings: list(d.savings).map(toModelCost),
  unpriced: list(d.unpriced).map(String),
});

const emptyCosts = (): Costs => toCosts({});

/** The query fields that are set, in the wire's names, as strings. */
function query(fields: Record<string, string | number | Date | undefined>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(fields)) {
    if (value === undefined || value === "" || value === 0) continue;
    out[key] = value instanceof Date ? value.toISOString().replace(/\.\d+Z$/, "Z") : String(value);
  }
  return out;
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
  /**
   * "native" runs the engine in this process through libgascoigne (needs koffi) and throws
   * NativeError when no library is found; "proxy" talks to the gascoigne server.
   * Default `$GASCOIGNE_MODE`, else "proxy". See spec/native.md.
   */
  mode?: "proxy" | "native";
  /** Configuration for the embedded engine, merged by the library. */
  settings?: Settings;
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
  private native?: Native;

  /** Throws NativeError in native mode when no library can be found or loaded. */
  constructor(private readonly opts: Options = {}) {
    if (this.mode() === "native") this.native = Native.open(opts.settings ?? {});
  }

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
        this.warn(
          `gascoigne server speaks proto ${proto}, SDK ${PROTO}; running without optimization`,
        );
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
      this.warn(
        `gascoigne-cli not found on PATH; running without optimization. Install: ${INSTALL_HINT}`,
      );
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

  private mode(): string {
    return this.opts.mode ?? (process.env.GASCOIGNE_MODE || "proxy");
  }

  /** Release the embedded engine, if any. */
  close(): void {
    this.native?.close();
    this.native = undefined;
    this.state = "bypass";
  }

  /** True when optimize calls will be tried. Probes once, then remembers. */
  async ready(): Promise<boolean> {
    if (this.disabled()) return false;
    if (this.state === "unknown") {
      this.probing ??= (async () => {
        const up =
          this.native !== undefined || (await this.healthy()) || (await this.startServer());
        this.state = up ? "ready" : "bypass";
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
    const request: OptimizeRequest = {
      text,
      agent: this.opts.agent,
      session: this.opts.session,
      ...attrs,
    };
    try {
      // undefined fields are not serialized
      const body = JSON.stringify(request);
      const out = this.native
        ? toResult(JSON.parse(await this.native.optimize(body)) as OptimizeResponse)
        : await this.post(body);
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

  private async post(body: string): Promise<Result> {
    const r = await fetch(`${this.baseUrl}/sdk/v1/optimize`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
      signal: AbortSignal.timeout(this.opts.timeoutMs ?? 5000),
    });
    if (!r.ok) throw new Error(`status ${r.status}`);
    return toResult((await r.json()) as OptimizeResponse);
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
      if (this.native) return await this.native.raw(rawId);
      const r = await fetch(`${this.baseUrl}/sdk/v1/raw/${encodeURIComponent(rawId)}`, {
        signal: AbortSignal.timeout(this.opts.timeoutMs ?? 5000),
      });
      return r.ok ? await r.text() : "";
    } catch {
      this.failed();
      return "";
    }
  }

  /**
   * The recorded runs summed per group. Reads never throw and never trip the optimize breaker:
   * on any failure (bypass, server down, a bad query) the answer is an empty list.
   */
  async totals(q: TotalsQuery = {}): Promise<Total[]> {
    const params = query({
      by: q.by,
      session: q.session,
      agent: q.agent,
      model: q.model,
      since: q.since,
    });
    return list(
      await this.read("/sdk/v1/stats", params, (p) => this.native?.stats(JSON.stringify(p))),
    ).map(toTotal);
  }

  /** The recorded runs, newest first; empty on any failure. */
  async runs(q: RunsQuery = {}): Promise<Run[]> {
    const params = query({
      session: q.session,
      agent: q.agent,
      model: q.model,
      since: q.since,
      before: q.before,
      limit: q.limit,
    });
    const native = (p: Record<string, string>) =>
      this.native?.recent(
        JSON.stringify({
          ...p,
          ...(p.before ? { before: Number(p.before) } : {}),
          ...(p.limit ? { limit: Number(p.limit) } : {}),
        }),
      );
    return list(await this.read("/sdk/v1/recent", params, native)).map(toRun);
  }

  /** What the tokens saved are worth, an estimate not a bill; an empty `Costs` on any failure. */
  async costs(q: Omit<TotalsQuery, "by"> = {}): Promise<Costs> {
    const params = query({ session: q.session, agent: q.agent, model: q.model, since: q.since });
    const data = await this.read("/sdk/v1/costs", params, (p) =>
      this.native?.costs(JSON.stringify(p)),
    );
    return data && !Array.isArray(data) ? toCosts(data as Wire) : emptyCosts();
  }

  /** A ledger read: the parsed JSON, or undefined on any failure. */
  private async read(
    path: string,
    params: Record<string, string>,
    viaNative: (params: Record<string, string>) => Promise<string> | undefined,
  ): Promise<unknown> {
    if (!(await this.ready())) return undefined;
    try {
      if (this.native) {
        const out = viaNative(params) ?? Promise.reject(new Error("no engine"));
        return JSON.parse(await out);
      }
      const r = await fetch(`${this.baseUrl}${path}?${new URLSearchParams(params)}`, {
        signal: AbortSignal.timeout(this.opts.timeoutMs ?? 5000),
      });
      return r.ok ? await r.json() : undefined;
    } catch {
      return undefined;
    }
  }

  /** Base URL that routes an LLM client through the gascoigne proxy, or undefined in bypass. */
  async proxyBaseUrl(
    api: "openai" | "anthropic" | "gemini" = "openai",
  ): Promise<string | undefined> {
    // The embedded engine has no listening proxy.
    if (!(await this.ready()) || this.native) return undefined;
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
export const totals = (q?: TotalsQuery) => current.totals(q);
export const runs = (q?: RunsQuery) => current.runs(q);
export const costs = (q?: Omit<TotalsQuery, "by">) => current.costs(q);
