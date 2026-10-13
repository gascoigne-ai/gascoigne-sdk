package ai.gascoigne.demo.springai.wrap;

import ai.gascoigne.Gascoigne;
import ai.gascoigne.demo.Demo;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

/** Spring AI + OpenRouter. Two added lines (marked). */
@SpringBootApplication
public class Application {

    public static void main(String[] args) {
        // OpenRouter settings from the nearest .env.
        ai.gascoigne.demo.OpenRouter.fromEnv();
        SpringApplication.run(Application.class, args);
    }

    // 1. Start gascoigne.
    @Bean
    Gascoigne gascoigne() {
        return Gascoigne.builder().agent("spring-ai").onResult(Demo::observe).build();
    }

    @Bean
    CommandLineRunner run(ChatClient.Builder chat, LogTools tools, Gascoigne gascoigne) {
        return args -> {
            if (Demo.dry()) {
                tools.searchLogs();
                Demo.report(gascoigne.stats(), null);
                return;
            }
            String answer = chat.build().prompt(Demo.PROMPT).tools(tools).call().content();
            Demo.report(gascoigne.stats(), answer);
        };
    }
}
