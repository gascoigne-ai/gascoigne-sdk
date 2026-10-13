package ai.gascoigne.demo.springai.auto;

import ai.gascoigne.Gascoigne;
import ai.gascoigne.demo.Demo;
import ai.gascoigne.demo.OpenRouter;
import ai.gascoigne.spring.EnableGascoigne;
import ai.gascoigne.spring.RetrieveOriginalTool;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

/**
 * Spring AI with gascoigne enabled for every tool call by one explicit annotation. The tool
 * itself, and the MCP tools if there were any, know nothing about gascoigne.
 */
// 1. Opt in, explicitly: without this annotation nothing is decorated.
@EnableGascoigne(skip = {"write_file", "retrieve_original"})
@SpringBootApplication
public class Application {

    public static void main(String[] args) {
        OpenRouter.fromEnv();
        SpringApplication.run(Application.class, args);
    }

    /** Optional: your own client, here only to report what was saved. */
    @Bean
    Gascoigne gascoigne() {
        return Gascoigne.builder().agent("spring-ai").onResult(Demo::observe).build();
    }

    @Bean
    CommandLineRunner run(ChatClient.Builder chat, LogTools tools, Gascoigne gascoigne) {
        return args -> {
            if (Demo.dry()) {
                System.out.println("Dry run: tool calls are decorated inside the LLM loop.");
                return;
            }
            String answer = chat.build()
                    .prompt(Demo.PROMPT)
                    .tools(tools, new RetrieveOriginalTool(gascoigne))
                    .call()
                    .content();
            Demo.report(gascoigne.stats(), answer);
        };
    }
}
