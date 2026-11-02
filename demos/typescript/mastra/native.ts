/** Mastra, native: the engine runs inside this process. No server, no CLI. */
import { init, wrapTool } from "@gascoigne-ai/sdk";
import { Agent } from "@mastra/core/agent";
import { createTool } from "@mastra/core/tools";
import { createOpenRouter } from "@openrouter/ai-sdk-provider";
import { z } from "zod";
import { openrouter, PROMPT, run, searchLogs } from "../kit.js";

// 1. Start gascoigne in native mode. It throws if libgascoigne cannot be found.
init({ agent: "mastra", mode: "native" });

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
