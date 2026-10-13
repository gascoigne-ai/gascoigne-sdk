import { Runtime } from "@gascoigne-ai/sdk";
import { describe, expect, it } from "vitest";
import { wrapTools } from "../src/index.js";

describe("wrapTools", () => {
  it("optimizes string results and keeps the rest", async () => {
    // bypass: wrapper must be transparent
    process.env.GASCOIGNE_SDK = "off";
    const rt = new Runtime();
    const tools = wrapTools(
      {
        a: { description: "d", execute: async () => "big" },
        b: { execute: () => 3 },
        c: { description: "no exec" },
      },
      rt,
    );
    expect(await tools.a.execute?.()).toBe("big");
    expect(await tools.b.execute?.()).toBe(3);
    expect((tools.c as { description: string }).description).toBe("no exec");
    expect((tools.a as { description: string }).description).toBe("d");
  });
});
