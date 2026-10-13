/** Mastra agent with the OpenRouter provider. Two added lines. */
import { init, wrapTool } from "@gascoigne-ai/sdk";
import { Agent } from "@mastra/core/agent";
import { createTool } from "@mastra/core/tools";
import { createOpenRouter } from "@openrouter/ai-sdk-provider";
import { z } from "zod";
import { openrouter, PROMPT, run, searchLogs } from "../kit.js";

// 1. Start gascoigne.
init({ agent: "mastra" });

// 2. Wrap the tool.
const logs = wrapTool(searchLogs, "search_logs");

const agent = new Agent({
  id: "logs",
  name: "logs",
  instructions: "Answer from the tools.",
  model: createOpenRouter({ apiKey: openrouter.apiKey })(openrouter.model),
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
