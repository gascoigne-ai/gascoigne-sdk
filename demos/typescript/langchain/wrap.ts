/** LangChain.js `createAgent` (a LangGraph.js graph). Two added lines. */
import { init, wrapTool } from "@gascoigne-ai/sdk";
import { tool } from "@langchain/core/tools";
import { ChatOpenAI } from "@langchain/openai";
import { createAgent } from "langchain";
import { z } from "zod";
import { openrouter, PROMPT, run, searchLogs } from "../kit.js";

// 1. Start gascoigne.
init({ agent: "langchain-js" });

// 2. Wrap the tool.
const logs = wrapTool(searchLogs, "search_logs");

const searchTool = tool(async () => String(await logs()), {
  name: "search_logs",
  description: "Return the recent service logs.",
  schema: z.object({}),
});
const agent = createAgent({
  model: new ChatOpenAI({
    model: openrouter.model,
    apiKey: openrouter.apiKey,
    configuration: { baseURL: openrouter.baseURL },
  }),
  tools: [searchTool],
});

await run(
  async () =>
    (await agent.invoke({ messages: [{ role: "user", content: PROMPT }] })).messages.at(-1)
      ?.content,
  logs,
);
