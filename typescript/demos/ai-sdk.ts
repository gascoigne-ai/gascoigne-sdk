/** Vercel AI SDK + OpenRouter. Two added lines. */
import { wrapTools } from "@gascoigne/ai-sdk";
import { init } from "@gascoigne/sdk";
import { createOpenRouter } from "@openrouter/ai-sdk-provider";
import { generateText, stepCountIs, tool } from "ai";
import { z } from "zod";
import { openrouter, PROMPT, run, searchLogs } from "./kit.js";

init({ agent: "vercel-ai-sdk" }); // 1. start gascoigne

const tools = wrapTools({
  // 2. wrap the tools
  search_logs: tool({
    description: "Return the recent service logs.",
    inputSchema: z.object({}),
    execute: async () => searchLogs(),
  }),
});

const { model, apiKey } = openrouter();
await run(
  async () =>
    (
      await generateText({
        model: createOpenRouter({ apiKey })(model),
        tools,
        stopWhen: stepCountIs(5),
        prompt: PROMPT,
      })
    ).text,
  () => tools.search_logs.execute?.({}, {} as never),
);
