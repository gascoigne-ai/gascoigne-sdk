/** LangChain.js `createAgent` (a LangGraph.js graph). Two added lines. */
import { init, wrapTool } from "@gascoigne/sdk";
import { tool } from "@langchain/core/tools";
import { ChatOpenAI } from "@langchain/openai";
import { createAgent } from "langchain";
import { z } from "zod";
import { openrouter, PROMPT, run, searchLogs } from "./kit.js";

init({ agent: "langchain-js" }); // 1. start gascoigne
const logs = wrapTool(searchLogs, "search_logs"); // 2. wrap the tool

const searchTool = tool(async () => String(await logs()), {
  name: "search_logs",
  description: "Return the recent service logs.",
  schema: z.object({}),
});
const { model, apiKey, baseURL } = openrouter();
const agent = createAgent({
  model: new ChatOpenAI({ model, apiKey, configuration: { baseURL } }),
  tools: [searchTool],
});

await run(
  async () =>
    (await agent.invoke({ messages: [{ role: "user", content: PROMPT }] })).messages.at(-1)?.content,
  logs,
);
