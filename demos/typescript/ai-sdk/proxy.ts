/** Vercel AI SDK through the gascoigne proxy: tools are not wrapped, one added line. */
import { init, proxyBaseUrl } from "@gascoigne/sdk";
import { createOpenRouter } from "@openrouter/ai-sdk-provider";
import { generateText, stepCountIs, tool } from "ai";
import { z } from "zod";
import { openrouter, PROMPT, runProxy, searchLogs } from "../kit.js";

// 1. Start gascoigne.
init({ agent: "vercel-ai-sdk" });

// 2. Send LLM traffic through the gascoigne proxy.
const baseURL = (await proxyBaseUrl("openai")) ?? openrouter.baseURL;

const openRouter = createOpenRouter({ apiKey: openrouter.apiKey, baseURL });
const tools = {
  search_logs: tool({
    description: "Return the recent service logs.",
    inputSchema: z.object({}),
    execute: async () => searchLogs(),
  }),
};

await runProxy(
  async () =>
    (
      await generateText({
        model: openRouter(openrouter.model),
        tools,
        stopWhen: stepCountIs(5),
        prompt: PROMPT,
      })
    ).text,
);
