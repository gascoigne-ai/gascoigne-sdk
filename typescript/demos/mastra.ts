/** Mastra agent with the OpenRouter provider. Two added lines. */
import { init, wrapTool } from "@gascoigne/sdk";
import { Agent } from "@mastra/core/agent";
import { createTool } from "@mastra/core/tools";
import { createOpenRouter } from "@openrouter/ai-sdk-provider";
import { z } from "zod";
import { openrouter, PROMPT, run, searchLogs } from "./kit.js";

init({ agent: "mastra" }); // 1. start gascoigne
const logs = wrapTool(searchLogs, "search_logs"); // 2. wrap the tool

const { model, apiKey } = openrouter();
const agent = new Agent({
  id: "logs",
  name: "logs",
  instructions: "Answer from the tools.",
  model: createOpenRouter({ apiKey })(model),
  tools: {
    search_logs: createTool({
      id: "search_logs",
      description: "Return the recent service logs.",
      inputSchema: z.object({}),
      execute: async () => ({ logs: await logs() }),
    }),
  },
});

await run(async () => (await agent.generate(PROMPT)).text, logs);
