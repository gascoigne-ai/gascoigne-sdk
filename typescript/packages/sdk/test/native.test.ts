import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { gzipSync } from "node:zlib";
import { afterEach, describe, expect, it } from "vitest";
import { Runtime } from "../src/index.js";
import { findLibrary, unpack } from "../src/native.js";

const LIB = resolve(__dirname, "../../../../native/dist/libgascoigne.so");
const BUNDLE = resolve(__dirname, "../../../native-template/lib/linux-amd64/libgascoigne.so.gz");
const hasKoffi = await import("koffi").then(
  () => true,
  () => false,
);

afterEach(() => {
  delete process.env.GASCOIGNE_LIB;
});

describe("embedded mode", () => {
  it("throws and names where it looked when no library is found", () => {
    process.env.GASCOIGNE_LIB = "/nonexistent/libgascoigne.so";
    expect(() => new Runtime({ mode: "native" })).toThrow(/libgascoigne not found.*GASCOIGNE_LIB/);
  });

  it("searches the system directories", () => {
    delete process.env.GASCOIGNE_LIB;
    process.env.GASCOIGNE_UNPACK = "off";
    const dir = mkdtempSync(join(tmpdir(), "gas-sys-"));
    process.env.GASCOIGNE_LIB_PATH = dir;
    expect(findLibrary().path).toBeUndefined();
    const lib = join(dir, "libgascoigne.so");
    writeFileSync(lib, "x");
    expect(findLibrary().path).toBe(lib);
    delete process.env.GASCOIGNE_LIB_PATH;
    delete process.env.GASCOIGNE_UNPACK;
  });

  it.skipIf(!hasKoffi || !existsSync(LIB))("optimizes and returns the original", async () => {
    process.env.GASCOIGNE_LIB = LIB;
    const db = join(mkdtempSync(join(tmpdir(), "gas-")), "l.db");
    const rt = new Runtime({
      mode: "native",
      settings: { ignoreUserFile: true, config: `extensions:\n  ledger:\n    path: ${db}\n` },
    });
    const raw = "INFO request served path=/api/items status=200 ms=12\n".repeat(400);
    const res = await rt.optimizeResult(raw, { tool: "bash", cmd: "tail app.log" });
    expect(res.outTokens).toBeLessThan(res.rawTokens);
    expect(await rt.raw(res.rawId)).toBe(raw);
    expect(await rt.proxyBaseUrl()).toBeUndefined();
    rt.close();
  });

  it("unpacks a bundle once, into a hash-named folder, and rewrites a tampered file", () => {
    const dir = mkdtempSync(join(tmpdir(), "gas-unpack-"));
    process.env.GASCOIGNE_LIB_DIR = join(dir, "out");
    const gz = join(dir, "libgascoigne.so.gz");
    writeFileSync(gz, gzipSync(Buffer.from("library bytes")));
    const first = unpack(gz);
    expect(readFileSync(first, "utf8")).toBe("library bytes");
    expect(first).toContain("gascoigne-native-");
    expect(unpack(gz)).toBe(first);
    writeFileSync(first, "tampered");
    expect(readFileSync(unpack(gz), "utf8")).toBe("library bytes");
    delete process.env.GASCOIGNE_LIB_DIR;
  });

  it.skipIf(!hasKoffi || !existsSync(BUNDLE))(
    "loads a bundled library unpacked to a temp dir",
    () => {
      delete process.env.GASCOIGNE_LIB;
      const dir = mkdtempSync(join(tmpdir(), "gas-bundle-"));
      process.env.GASCOIGNE_LIB_DIR = dir;
      // The platform package is resolved by name in an application; here the same file is unpacked
      // directly and handed over as $GASCOIGNE_LIB.
      process.env.GASCOIGNE_LIB = unpack(BUNDLE);
      const db = join(dir, "l.db");
      const rt = new Runtime({
        mode: "native",
        settings: { ignoreUserFile: true, config: `extensions:\n  ledger:\n    path: ${db}\n` },
      });
      return rt.optimizeResult("INFO request served path=/api/items\n".repeat(400)).then((res) => {
        expect(res.rawId).not.toBe("");
        rt.close();
        delete process.env.GASCOIGNE_LIB_DIR;
      });
    },
  );
});
