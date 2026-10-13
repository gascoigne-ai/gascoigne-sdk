/** LangChain.js `createAgent` (a LangGraph.js graph under the hood). */
import { wrapTool } from "@gascoigne/sdk";
import { tool } from "@langchain/core/tools";
import { ChatOpenAI } from "@langchain/openai";
import { createAgent } from "langchain";
import { z } from "zod";
import * as common from "./common.js";

common.runtime("langchain-js");
const searchLogs = wrapTool(common.searchLogs, "search_logs");
const logs = tool(async () => (await searchLogs()) as string, {
  name: "search_logs",
  description: "Return the recent service logs.",
  schema: z.object({}),
});
const model = new ChatOpenAI({
  model: common.MODEL,
  apiKey: common.apiKey(),
  configuration: { baseURL: common.BASE_URL },
});
const agent = createAgent({ model, tools: [logs] });

if (common.dry()) await common.dryCall(() => logs.invoke({}));
else {
  const out = await agent.invoke({ messages: [{ role: "user", content: common.PROMPT }] });
  common.report(String(out.messages.at(-1)?.content ?? ""));
}
