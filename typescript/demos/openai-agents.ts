/** OpenAI Agents SDK for JS, chat completions via OpenRouter. Two added lines. */
import { init, wrapTool } from "@gascoigne/sdk";
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
import { openrouter, PROMPT, run, searchLogs } from "./kit.js";

init({ agent: "openai-agents-js" }); // 1. start gascoigne
const logs = wrapTool(searchLogs, "search_logs"); // 2. wrap the tool

const { model, apiKey, baseURL } = openrouter();
setTracingDisabled(true);
setOpenAIAPI("chat_completions");
setDefaultOpenAIClient(new OpenAI({ baseURL, apiKey }));
const agent = new Agent({
  name: "logs",
  model,
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
