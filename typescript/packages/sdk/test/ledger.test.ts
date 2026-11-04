import { existsSync, mkdtempSync, readdirSync } from "node:fs";
import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { Runtime } from "../src/index.js";

const LIB = resolve(__dirname, "../../../../native/dist/libgascoigne.so");
const hasKoffi = await import("koffi").then(
  () => true,
  () => false,
);

let srv: Server | undefined;
const urls: string[] = [];

async function serve(status = 200) {
  srv = createServer((req, res) => {
    res.setHeader("content-type", "application/json");
    if (req.url === "/sdk/v1/health") return res.end(JSON.stringify({ version: "t", proto: 1 }));
    urls.push(req.url ?? "");
    res.statusCode = status;
    if (status !== 200) return res.end("boom");
    if (req.url?.startsWith("/sdk/v1/stats"))
      return res.end(
        JSON.stringify([
          {
            group: "sdk",
            runs: 2,
            optimized: 2,
            failed: 0,
            raw_tokens: 100,
            out_tokens: 40,
            saved: 60,
          },
        ]),
      );
    if (req.url?.startsWith("/sdk/v1/recent"))
      return res.end(
        JSON.stringify([
          {
            id: 7,
            time: "2026-11-01T10:00:00Z",
            session: "s1",
            raw_tokens: 100,
            out_tokens: 10,
            raw_id: "abc",
            outcome: "optimized",
            optimizers: ["log"],
          },
        ]),
      );
    return res.end(
      JSON.stringify({
        billing: "api",
        first_read_usd: 0.5,
        in_context_usd: 1.5,
        rereads: 110,
        savings: [
          {
            model: "m",
            source: "static",
            tokenizer: "o200k",
            tokens: 10,
            model_tokens: 10,
            first_read_usd: 0.5,
            in_context_usd: 1.5,
          },
        ],
      }),
    );
  });
  const s = srv;
  await new Promise<void>((r) => s.listen(0, "127.0.0.1", r));
  process.env.GASCOIGNE_SERVER_ADDR = `127.0.0.1:${(s.address() as AddressInfo).port}`;
}

beforeEach(() => {
  urls.length = 0;
  for (const k of ["GASCOIGNE_SDK", "GASCOIGNE_SERVER", "GASCOIGNE_BIN"]) delete process.env[k];
});
afterEach(async () => {
  await new Promise((r) => (srv ? srv.close(r) : r(null)));
  srv = undefined;
});

describe("ledger reads through the server", () => {
  it("totals, runs and costs map the wire to camelCase and send the query", async () => {
    await serve();
    const rt = new Runtime();
    const totals = await rt.totals({
      by: "agent",
      session: "s 1",
      since: new Date("2026-11-01T00:00:00Z"),
    });
    expect(totals).toEqual([
      {
        group: "sdk",
        runs: 2,
        optimized: 2,
        failed: 0,
        rawTokens: 100,
        outTokens: 40,
        saved: 60,
        first: "",
        last: "",
      },
    ]);
    expect(urls[0]).toBe("/sdk/v1/stats?by=agent&session=s+1&since=2026-11-01T00%3A00%3A00Z");
    const runs = await rt.runs({ session: "s1", limit: 5, before: 9 });
    expect(runs[0]).toMatchObject({
      id: 7,
      rawId: "abc",
      optimizers: ["log"],
      outcome: "optimized",
    });
    expect(urls[1]).toBe("/sdk/v1/recent?session=s1&before=9&limit=5");
    const costs = await rt.costs();
    expect(costs.billing).toBe("api");
    expect(costs.inContextUsd).toBe(1.5);
    expect(costs.savings[0]).toMatchObject({ model: "m", source: "static", inContextUsd: 1.5 });
  });

  it("never throws and never trips the optimize breaker", async () => {
    await serve(500);
    const rt = new Runtime();
    for (let i = 0; i < 10; i++) expect(await rt.totals()).toEqual([]);
    expect(await rt.runs()).toEqual([]);
    expect((await rt.costs()).billing).toBe("");
    expect(await rt.ready()).toBe(true);
  });

  it("is empty in bypass", async () => {
    process.env.GASCOIGNE_SDK = "off";
    const rt = new Runtime();
    expect(await rt.totals()).toEqual([]);
    expect((await rt.costs()).savings).toEqual([]);
    delete process.env.GASCOIGNE_SDK;
  });
});

describe("embedded memory ledger", () => {
  it.skipIf(!hasKoffi || !existsSync(LIB))("counts runs without writing a file", async () => {
    process.env.GASCOIGNE_LIB = LIB;
    process.env.GASCOIGNE_LEDGER = "";
    const data = mkdtempSync(resolve(tmpdir(), "gas-mem-"));
    process.env.XDG_DATA_HOME = data;
    const rt = new Runtime({
      mode: "native",
      agent: "sdk",
      session: "s1",
      settings: {
        ignoreUserFile: true,
        ledger: "memory",
        pricing: { prices: { "acme-large": { in: 3, out: 15, tokenizer: "claude" } } },
      },
    });
    const raw = "INFO request served path=/api/items status=200 ms=12\n".repeat(400);
    await rt.optimizeResult(raw, { tool: "bash", cmd: "tail app.log", model: "acme-large" });
    const totals = await rt.totals({ by: "agent" });
    expect(totals.map((t) => [t.group, t.runs])).toEqual([["sdk", 1]]);
    expect(totals[0]?.saved).toBeGreaterThan(0);
    const runs = await rt.runs({ session: "s1" });
    expect(runs).toHaveLength(1);
    expect(runs[0]?.rawId).not.toBe("");
    const costs = await rt.costs();
    expect(costs.inContextUsd).toBeGreaterThan(0);
    expect(costs.savings[0]?.source).toBe("static");
    expect(await rt.totals({ by: "nonsense" })).toEqual([]);
    expect(readdirSync(data)).toEqual([]);
    rt.close();
    delete process.env.GASCOIGNE_LIB;
    delete process.env.GASCOIGNE_LEDGER;
    delete process.env.XDG_DATA_HOME;
  });
});
