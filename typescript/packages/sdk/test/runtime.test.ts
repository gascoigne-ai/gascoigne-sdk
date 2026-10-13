import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { Runtime } from "../src/index.js";

let srv: Server | undefined;
const posts: string[] = [];

async function serve(opts: { proto?: number; optimizeStatus?: number } = {}) {
  srv = createServer((req, res) => {
    if (req.url === "/sdk/v1/health") {
      res.setHeader("content-type", "application/json");
      return res.end(JSON.stringify({ version: "t", proto: opts.proto ?? 1, proxy: true }));
    }
    let body = "";
    req.on("data", (c) => (body += c));
    req.on("end", () => {
      if (req.url === "/sdk/v1/optimize") {
        posts.push(body);
        res.statusCode = opts.optimizeStatus ?? 200;
        return res.end(
          JSON.stringify({ text: "short", raw_id: "abc", raw_tokens: 100, out_tokens: 5 }),
        );
      }
      res.end("original");
    });
  });
  const s = srv;
  await new Promise<void>((r) => s.listen(0, "127.0.0.1", r));
  process.env.GASCOIGNE_SERVER_ADDR = `127.0.0.1:${(s.address() as AddressInfo).port}`;
}

beforeEach(() => {
  posts.length = 0;
  for (const k of ["GASCOIGNE_SDK", "GASCOIGNE_SERVER", "GASCOIGNE_BIN"]) delete process.env[k];
});
afterEach(async () => {
  await new Promise((r) => (srv ? srv.close(r) : r(null)));
  srv = undefined;
});

describe("Runtime", () => {
  it("warns once and passes through when the CLI is missing", async () => {
    process.env.GASCOIGNE_SERVER_ADDR = "127.0.0.1:9";
    const saved = process.env.PATH;
    process.env.PATH = "";
    const warnings: string[] = [];
    try {
      const rt = new Runtime({ warn: (m) => warnings.push(m) });
      expect(await rt.optimize("hello ".repeat(50))).toBe("hello ".repeat(50));
      expect(await rt.optimize("again")).toBe("again");
      expect(await rt.proxyBaseUrl()).toBeUndefined();
      expect(await rt.raw("x")).toBe("");
    } finally {
      process.env.PATH = saved;
    }
    expect(warnings).toHaveLength(1);
    expect(warnings[0]).toContain("not found on PATH");
  });

  it("kill switch bypasses silently", async () => {
    process.env.GASCOIGNE_SDK = "off";
    const warnings: string[] = [];
    expect(await new Runtime({ warn: (m) => warnings.push(m) }).optimize("x")).toBe("x");
    expect(warnings).toHaveLength(0);
  });

  it("optimizes through the server and reports", async () => {
    await serve();
    const seen: string[] = [];
    const rt = new Runtime({ agent: "demo", onResult: (_o, r) => seen.push(r.rawId) });
    const res = await rt.optimizeResult("long ".repeat(100), { tool: "grep" });
    expect(res).toMatchObject({ text: "short", rawId: "abc", outTokens: 5 });
    expect(JSON.parse(posts[0])).toMatchObject({ agent: "demo", tool: "grep" });
    expect(seen).toEqual(["abc"]);
    expect(rt.stats()).toEqual({ rawTokens: 100, outTokens: 5 });
    expect(await rt.proxyBaseUrl()).toMatch(/\/v1$/);
    expect(await rt.raw("abc")).toBe("original");
  });

  it("bypasses on an unknown proto", async () => {
    await serve({ proto: 99 });
    const saved = process.env.PATH;
    process.env.PATH = "";
    try {
      expect(await new Runtime({ warn: () => {} }).optimize("x")).toBe("x");
    } finally {
      process.env.PATH = saved;
    }
    expect(posts).toHaveLength(0);
  });

  it("returns the input on failures and opens the breaker after five", async () => {
    await serve({ optimizeStatus: 500 });
    const rt = new Runtime();
    for (let i = 0; i < 7; i++) expect(await rt.optimize("text")).toBe("text");
    expect(posts).toHaveLength(5);
  });

  it("wrapTool optimizes strings only", async () => {
    await serve();
    const rt = new Runtime();
    expect(await rt.wrapTool(() => "big", "t")()).toBe("short");
    expect(await rt.wrapTool(async () => 3)()).toBe(3);
  });
});
