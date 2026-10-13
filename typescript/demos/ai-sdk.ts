/** Vercel AI SDK + OpenRouter provider. */
import { wrapTools } from "@gascoigne/ai-sdk";
import { createOpenRouter } from "@openrouter/ai-sdk-provider";
import { generateText, stepCountIs, tool } from "ai";
import { z } from "zod";
import * as common from "./common.js";

common.runtime("vercel-ai-sdk");
const openrouter = createOpenRouter({ apiKey: common.apiKey() });
const tools = wrapTools({
  search_logs: tool({
    description: "Return the recent service logs.",
    inputSchema: z.object({}),
    execute: async () => common.searchLogs(),
  }),
});

if (common.dry()) await common.dryCall(() => tools.search_logs.execute!({}, {} as never));
else {
  const { text } = await generateText({
    model: openrouter(common.MODEL),
    tools,
    stopWhen: stepCountIs(5),
    prompt: common.PROMPT,
  });
  common.report(text);
}
