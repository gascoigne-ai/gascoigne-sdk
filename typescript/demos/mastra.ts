/** Mastra agent with the OpenRouter provider. */
import { wrapTool } from "@gascoigne/sdk";
import { Agent } from "@mastra/core/agent";
import { createTool } from "@mastra/core/tools";
import { createOpenRouter } from "@openrouter/ai-sdk-provider";
import { z } from "zod";
import * as common from "./common.js";

common.runtime("mastra");
const searchLogs = wrapTool(common.searchLogs, "search_logs");
const logs = createTool({
  id: "search_logs",
  description: "Return the recent service logs.",
  inputSchema: z.object({}),
  execute: async () => ({ logs: await searchLogs() }),
});
const agent = new Agent({
  id: "logs",
  name: "logs",
  instructions: "Answer from the tools.",
  model: createOpenRouter({ apiKey: common.apiKey() })(common.MODEL),
  tools: { search_logs: logs },
});

if (common.dry()) await common.dryCall(searchLogs);
else common.report((await agent.generate(common.PROMPT)).text);
