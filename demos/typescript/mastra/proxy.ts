/** Mastra through the gascoigne proxy: tools are not wrapped, one added line. */
import { init, proxyBaseUrl } from "@gascoigne-ai/sdk";
import { Agent } from "@mastra/core/agent";
import { createTool } from "@mastra/core/tools";
import { createOpenRouter } from "@openrouter/ai-sdk-provider";
import { z } from "zod";
import { openrouter, PROMPT, runProxy, searchLogs } from "../kit.js";

// 1. Start gascoigne.
init({ agent: "mastra" });

// 2. Send LLM traffic through the gascoigne proxy.
const baseURL = (await proxyBaseUrl("openai")) ?? openrouter.baseURL;

const agent = new Agent({
  id: "logs",
  name: "logs",
  instructions: "Answer from the tools.",
  model: createOpenRouter({ apiKey: openrouter.apiKey, baseURL })(openrouter.model),
  tools: {
    search_logs: createTool({
      id: "search_logs",
      description: "Return the recent service logs.",
      inputSchema: z.object({}),
      execute: async () => ({ logs: searchLogs() }),
    }),
  },
});

await runProxy(async () => (await agent.generate(PROMPT)).text);
