/** LangChain.js through the gascoigne proxy: tools are not wrapped, one added line. */
import { init, proxyBaseUrl } from "@gascoigne/sdk";
import { tool } from "@langchain/core/tools";
import { ChatOpenAI } from "@langchain/openai";
import { createAgent } from "langchain";
import { z } from "zod";
import { openrouter, PROMPT, runProxy, searchLogs } from "../kit.js";

// 1. Start gascoigne.
init({ agent: "langchain-js" });

// 2. Send LLM traffic through the gascoigne proxy.
const baseURL = (await proxyBaseUrl("openai")) ?? openrouter.baseURL;

const logs = tool(async () => searchLogs(), {
  name: "search_logs",
  description: "Return the recent service logs.",
  schema: z.object({}),
});
const model = new ChatOpenAI({
  model: openrouter.model,
  apiKey: openrouter.apiKey,
  configuration: { baseURL },
});
const agent = createAgent({ model, tools: [logs] });

await runProxy(
  async () =>
    (await agent.invoke({ messages: [{ role: "user", content: PROMPT }] })).messages.at(-1)
      ?.content,
);
