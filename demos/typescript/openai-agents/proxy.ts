/** OpenAI Agents SDK for JS through the gascoigne proxy: tools are not wrapped. */
import { init, proxyBaseUrl } from "@gascoigne/sdk";
import {
  Agent,
  run,
  setDefaultOpenAIClient,
  setOpenAIAPI,
  setTracingDisabled,
  tool,
} from "@openai/agents";
import OpenAI from "openai";
import { z } from "zod";
import { openrouter, PROMPT, runProxy, searchLogs } from "../kit.js";

// 1. Start gascoigne.
init({ agent: "openai-agents-js" });

// 2. Send LLM traffic through the gascoigne proxy.
const baseURL = (await proxyBaseUrl("openai")) ?? openrouter.baseURL;

setTracingDisabled(true);
setOpenAIAPI("chat_completions");
setDefaultOpenAIClient(new OpenAI({ baseURL, apiKey: openrouter.apiKey }));
const agent = new Agent({
  name: "logs",
  model: openrouter.model,
  tools: [
    tool({
      name: "search_logs",
      description: "Return the recent service logs.",
      parameters: z.object({}),
      execute: async () => searchLogs(),
    }),
  ],
});

await runProxy(async () => (await run(agent, PROMPT)).finalOutput);
