package ai.gascoigne.demo.langchain4j.wrap;

import ai.gascoigne.Attrs;
import ai.gascoigne.Gascoigne;
import ai.gascoigne.demo.Demo;
import ai.gascoigne.demo.OpenRouter;
import dev.langchain4j.agent.tool.Tool;
import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.service.AiServices;

/** LangChain4j + OpenRouter. Two added lines (marked). */
public final class Main {

    interface Assistant {
        String chat(String message);
    }

    /** The tool the model can call. */
    static final class LogTools {
        private final Gascoigne gascoigne;

        LogTools(Gascoigne gascoigne) {
            this.gascoigne = gascoigne;
        }

        @Tool(name = "search_logs", value = "Return the recent service logs.")
        String searchLogs() {
            // 2. Optimize what the tool returns.
            return gascoigne.optimize(Demo.noisyLogs(), Attrs.tool("search_logs"));
        }
    }

    public static void main(String[] args) {
        OpenRouter openRouter = OpenRouter.fromEnv();

        // 1. Start gascoigne.
        Gascoigne gascoigne =
                Gascoigne.builder().agent("langchain4j").onResult(Demo::observe).build();
        LogTools tools = new LogTools(gascoigne);

        if (Demo.dry()) {
            tools.searchLogs();
            Demo.report(gascoigne.stats(), null);
            return;
        }
        Assistant assistant = AiServices.builder(Assistant.class)
                .chatModel(OpenAiChatModel.builder()
                        .baseUrl(openRouter.baseUrl())
                        .apiKey(openRouter.apiKey())
                        .modelName(openRouter.model())
                        .build())
                .tools(tools)
                .build();
        Demo.report(gascoigne.stats(), assistant.chat(Demo.PROMPT));
    }
}
