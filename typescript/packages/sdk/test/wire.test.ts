import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { decodeHealth, decodeResult, decodeRuns, decodeTotals } from "../src/index.js";

const FIXTURES = resolve(__dirname, "../../../../spec/fixtures");
const load = (name: string): unknown => JSON.parse(readFileSync(resolve(FIXTURES, name), "utf8"));

describe("spec fixtures decode into the typed wire models", () => {
  it("covers every json fixture", () => {
    expect(
      readdirSync(FIXTURES)
        .filter((f) => f.endsWith(".json"))
        .sort(),
    ).toEqual([
      "health.json",
      "optimize_optimized.json",
      "optimize_skipped.json",
      "recent.json",
      "stats.json",
    ]);
  });

  it("health", () => {
    expect(decodeHealth(load("health.json"))).toEqual({
      version: "0.11.0 (8478f54)",
      proto: 1,
      proxy: true,
    });
  });

  it("optimized", () => {
    const r = decodeResult(load("optimize_optimized.json"));
    expect([r.rawId, r.rawTokens, r.outTokens, r.skipped]).toEqual(["a4e762ac", 9200, 34, ""]);
  });

  it("skipped", () => {
    const r = decodeResult(load("optimize_skipped.json"));
    expect([r.text, r.rawId, r.skipped]).toEqual(["ok", "", "1 tokens < min_tokens 200"]);
  });

  it("stats", () => {
    const totals = decodeTotals(load("stats.json"));
    expect(totals.map((t) => t.group)).toEqual(["default", "-"]);
    expect(totals[0]?.saved).toBe(9166);
    expect(totals[0]?.first.startsWith("2026-")).toBe(true);
  });

  it("recent keeps order and optional fields", () => {
    const runs = decodeRuns(load("recent.json"));
    expect(runs.map((r) => r.id)).toEqual([2, 1]);
    const [bypassed, optimized] = runs;
    expect(bypassed?.outcome).toBe("bypassed");
    expect(bypassed?.route).toBeUndefined();
    expect(bypassed?.optimizers).toEqual([]);
    expect(bypassed?.reason).not.toBe("");
    expect(optimized?.outcome).toBe("optimized");
    expect(optimized?.route).toBe("default");
    expect(optimized?.optimizers).toHaveLength(28);
    expect(optimized?.optimizers[0]).toBe("embedjson");
  });

  it("keeps unknown route and outcome values", () => {
    const [first] = load("recent.json") as Record<string, unknown>[];
    const [run] = decodeRuns([{ ...first, route: "custom", outcome: "new" }]);
    expect([run?.route, run?.outcome]).toEqual(["custom", "new"]);
  });

  it.each([
    ["result without text", () => decodeResult({ raw_tokens: 1, out_tokens: 1 })],
    [
      "result with string tokens",
      () => decodeResult({ text: "a", raw_tokens: "1", out_tokens: 1 }),
    ],
    ["total without runs", () => decodeTotals([{ group: "g" }])],
    [
      "run without outcome",
      () => decodeRuns([{ id: 1, time: "t", raw_tokens: 1, out_tokens: 1, duration_ns: 1 }]),
    ],
    ["health without proxy", () => decodeHealth({ version: "v", proto: 1 })],
    ["stats not a list", () => decodeTotals({ group: "g" })],
  ])("rejects %s", (_name, parse) => {
    expect(parse).toThrow();
  });
});
