/** OpenAI Agents SDK for JS, chat completions via OpenRouter. Two added lines. */
import { init, wrapTool } from "@gascoigne-ai/sdk";
import {
  Agent,
  run as runAgent,
  setDefaultOpenAIClient,
  setOpenAIAPI,
  setTracingDisabled,
  tool,
} from "@openai/agents";
import OpenAI from "openai";
import { z } from "zod";
import { openrouter, PROMPT, run, searchLogs } from "../kit.js";

// 1. Start gascoigne.
init({ agent: "openai-agents-js" });

// 2. Wrap the tool.
const logs = wrapTool(searchLogs, "search_logs");

setTracingDisabled(true);
setOpenAIAPI("chat_completions");
setDefaultOpenAIClient(new OpenAI({ baseURL: openrouter.baseURL, apiKey: openrouter.apiKey }));
const agent = new Agent({
  name: "logs",
  model: openrouter.model,
  tools: [
    tool({
      name: "search_logs",
      description: "Return the recent service logs.",
      parameters: z.object({}),
      execute: async () => String(await logs()),
    }),
  ],
});

await run(async () => (await runAgent(agent, PROMPT)).finalOutput, logs);
