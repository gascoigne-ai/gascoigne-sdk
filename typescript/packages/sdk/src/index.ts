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

export { NativeError, type Settings } from "./native.js";

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

/** Body of `GET /sdk/v1/health`. */
export interface Health {
  version: string;
  proto: number;
  proxy: boolean;
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

/** What happened to a recorded run. The server's set can grow, so other strings occur. */
export type Outcome =
  | "optimized"
  | "unchanged"
  | "bypassed"
  | "rerequested"
  | "error"
  | (string & {});

/** The optimizer chain a run took. Routes come from the server's config, so others occur. */
export type Route = "default" | "fold" | "skill" | "prompt" | "tools" | "image" | (string & {});

/** One recorded optimization. */
export interface Run {
  id: number;
  /** RFC 3339. */
  time: string;
  session: string;
  agent: string;
  model: string;
  command: string;
  /** Undefined when the server did not record one. */
  route?: Route;
  optimizers: string[];
  rawTokens: number;
  outTokens: number;
  durationNs: number;
  rawId: string;
  outcome: Outcome;
  reason: string;
}

/** Filters for `totals`; empty ones match everything. `by` is route (default),
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

function obj(value: unknown, what = "body"): Wire {
  if (typeof value !== "object" || value === null || Array.isArray(value))
    throw new Error(`${what} is not an object`);
  return value as Wire;
}

function str(record: Wire, key: string, required = false): string {
  const value = record[key];
  if (value === undefined && !required) return "";
  if (typeof value !== "string") throw new Error(`${key} is not a string`);
  return value;
}

function int(record: Wire, key: string, required = false): number {
  const value = record[key];
  if (value === undefined && !required) return 0;
  if (typeof value !== "number" || !Number.isInteger(value))
    throw new Error(`${key} is not an integer`);
  return value;
}

/** A missing or null list is empty. */
function strs(record: Wire, key: string): string[] {
  const value = record[key];
  if (value === undefined || value === null) return [];
  if (!Array.isArray(value) || !value.every((item) => typeof item === "string")) {
    throw new Error(`${key} is not a list of strings`);
  }
  return [...value];
}

function many<T>(body: unknown, decode: (item: Wire) => T): T[] {
  if (!Array.isArray(body)) throw new Error("body is not a list");
  return body.map((item) => decode(obj(item, "item")));
}

/** Decode `GET /sdk/v1/health`; throws when the body is not one. */
export function decodeHealth(body: unknown): Health {
  const record = obj(body);
  if (typeof record.proxy !== "boolean") throw new Error("proxy is not a boolean");
  return {
    version: str(record, "version", true),
    proto: int(record, "proto", true),
    proxy: record.proxy,
  };
}

/** Decode a `POST /sdk/v1/optimize` answer; throws when the body is not one. */
export function decodeResult(body: unknown): Result {
  const record = obj(body);
  return {
    text: str(record, "text", true),
    rawId: str(record, "raw_id"),
    rawTokens: int(record, "raw_tokens", true),
    outTokens: int(record, "out_tokens", true),
    skipped: str(record, "skipped"),
  };
}

const toTotal = (record: Wire): Total => ({
  group: str(record, "group", true),
  runs: int(record, "runs", true),
  optimized: int(record, "optimized", true),
  failed: int(record, "failed", true),
  rawTokens: int(record, "raw_tokens", true),
  outTokens: int(record, "out_tokens", true),
  saved: int(record, "saved", true),
  first: str(record, "first"),
  last: str(record, "last"),
});

const toRun = (record: Wire): Run => {
  const route = str(record, "route");
  return {
    id: int(record, "id", true),
    time: str(record, "time", true),
    session: str(record, "session"),
    agent: str(record, "agent"),
    model: str(record, "model"),
    command: str(record, "command"),
    ...(route ? { route } : {}),
    optimizers: strs(record, "optimizers"),
    rawTokens: int(record, "raw_tokens", true),
    outTokens: int(record, "out_tokens", true),
    durationNs: int(record, "duration_ns", true),
    rawId: str(record, "raw_id"),
    outcome: str(record, "outcome", true),
    reason: str(record, "reason"),
  };
};

/** Decode the body of `GET /sdk/v1/stats`. */
export const decodeTotals = (body: unknown): Total[] => many(body, toTotal);

/** Decode the body of `GET /sdk/v1/recent`, order kept. */
export const decodeRuns = (body: unknown): Run[] => many(body, toRun);

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

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

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
    (this.opts.warn ?? ((message) => console.warn(`[gascoigne] ${message}`)))(msg);
  }

  private async healthy(): Promise<boolean> {
    try {
      const r = await fetch(`${this.baseUrl}/sdk/v1/health`, { signal: AbortSignal.timeout(500) });
      if (!r.ok) return false;
      const { proto } = decodeHealth(await r.json());
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
        p.on("error", (error) => {
          clearTimeout(t);
          reject(error);
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
        ? decodeResult(JSON.parse(await this.native.optimize(body)))
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
    return decodeResult(await r.json());
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
  async totals(filter: TotalsQuery = {}): Promise<Total[]> {
    const params = query({
      by: filter.by,
      session: filter.session,
      agent: filter.agent,
      model: filter.model,
      since: filter.since,
    });
    const body = await this.read("/sdk/v1/stats", params, (payload) =>
      this.native?.stats(JSON.stringify(payload)),
    );
    return this.decoded(body, decodeTotals);
  }

  /** The recorded runs, newest first; empty on any failure. */
  async runs(filter: RunsQuery = {}): Promise<Run[]> {
    const params = query({
      session: filter.session,
      agent: filter.agent,
      model: filter.model,
      since: filter.since,
      before: filter.before,
      limit: filter.limit,
    });
    const native = (payload: Record<string, string>) =>
      this.native?.recent(
        JSON.stringify({
          ...payload,
          ...(payload.before ? { before: Number(payload.before) } : {}),
          ...(payload.limit ? { limit: Number(payload.limit) } : {}),
        }),
      );
    return this.decoded(await this.read("/sdk/v1/recent", params, native), decodeRuns);
  }

  /** Decode a ledger body; empty when there is none or it is malformed. */
  private decoded<T>(body: unknown, decode: (body: unknown) => T[]): T[] {
    if (body === undefined) return [];
    try {
      return decode(body);
    } catch {
      return [];
    }
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
export const wrapTool = <A extends unknown[], R>(
  fn: (...args: A) => R | Promise<R>,
  name?: string,
) => current.wrapTool(fn, name);
export const raw = (id: string) => current.raw(id);
export const proxyBaseUrl = (api?: "openai" | "anthropic" | "gemini") => current.proxyBaseUrl(api);
export const stats = () => current.stats();
export const totals = (filter?: TotalsQuery) => current.totals(filter);
export const runs = (filter?: RunsQuery) => current.runs(filter);
