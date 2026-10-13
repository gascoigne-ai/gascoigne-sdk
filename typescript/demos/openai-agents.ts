/** OpenAI Agents SDK for JS, chat-completions pointed at OpenRouter. */
import { wrapTool } from "@gascoigne/sdk";
import { Agent, run, setDefaultOpenAIClient, setOpenAIAPI, setTracingDisabled, tool } from "@openai/agents";
import OpenAI from "openai";
import { z } from "zod";
import * as common from "./common.js";

common.runtime("openai-agents-js");
setTracingDisabled(true);
setOpenAIAPI("chat_completions");
setDefaultOpenAIClient(new OpenAI({ baseURL: common.BASE_URL, apiKey: common.apiKey() }));
const searchLogs = wrapTool(common.searchLogs, "search_logs");
const logs = tool({
  name: "search_logs",
  description: "Return the recent service logs.",
  parameters: z.object({}),
  execute: async () => (await searchLogs()) as string,
});
const agent = new Agent({ name: "logs", model: common.MODEL, tools: [logs] });

if (common.dry()) await common.dryCall(searchLogs);
else common.report(String((await run(agent, common.PROMPT)).finalOutput));
