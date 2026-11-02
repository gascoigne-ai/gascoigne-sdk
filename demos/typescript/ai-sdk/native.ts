/** Vercel AI SDK, native: the engine runs inside this process. No server, no CLI. */
import { wrapTools } from "@gascoigne-ai/ai-sdk";
import { init } from "@gascoigne-ai/sdk";
import { createOpenRouter } from "@openrouter/ai-sdk-provider";
import { generateText, stepCountIs, tool } from "ai";
import { z } from "zod";
import { openrouter, PROMPT, run, searchLogs } from "../kit.js";

// 1. Start gascoigne in native mode. It throws if libgascoigne cannot be found.
init({ agent: "vercel-ai-sdk", mode: "native" });

const tools = wrapTools({
  // 2. Wrap the tools.
  search_logs: tool({
    description: "Return the recent service logs.",
    inputSchema: z.object({}),
    execute: async () => searchLogs(),
  }),
});

await run(
  async () =>
    (
      await generateText({
        model: createOpenRouter({ apiKey: openrouter.apiKey })(openrouter.model),
        tools,
        stopWhen: stepCountIs(5),
        prompt: PROMPT,
      })
    ).text,
  () => tools.search_logs.execute?.({}, {} as never),
);
