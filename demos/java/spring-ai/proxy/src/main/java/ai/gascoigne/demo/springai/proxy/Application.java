package ai.gascoigne.demo.springai.proxy;

import ai.gascoigne.Gascoigne;
import ai.gascoigne.demo.Demo;
import ai.gascoigne.demo.OpenRouter;
import java.net.http.HttpClient;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.SpringApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/**
 * Spring AI through the gascoigne proxy: the tool is a plain {@code @Tool} method that knows
 * nothing about gascoigne. One added line.
 */
@SpringBootApplication
public class Application {

    public static void main(String[] args) {
        OpenRouter openRouter = OpenRouter.fromEnv();

        // 1. Start gascoigne.
        Gascoigne gascoigne = Gascoigne.builder().agent("spring-ai").build();

        // 2. Send LLM traffic through the gascoigne proxy.
        String baseUrl = gascoigne.proxyBaseUrl("openai").orElse(openRouter.baseUrl());

        String baseUrlArg = "--spring.ai.openai.base-url=" + baseUrl;
        SpringApplication.run(Application.class, withArg(args, baseUrlArg));
    }

    private static String[] withArg(String[] args, String arg) {
        String[] all = java.util.Arrays.copyOf(args, args.length + 1);
        all[args.length] = arg;
        return all;
    }

    /** The JDK client offers an HTTP/2 upgrade on plain HTTP; a local HTTP/1.1 proxy needs none. */
    @Bean
    RestClient.Builder restClientBuilder() {
        HttpClient http = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).build();
        return RestClient.builder().requestFactory(new JdkClientHttpRequestFactory(http));
    }

    @Bean
    CommandLineRunner run(ChatClient.Builder chat, LogTools tools) {
        return args -> {
            if (Demo.dry()) {
                System.out.println("Dry run: the proxy rewrites LLM requests, nothing to show.");
                return;
            }
            long mark = Demo.proxyMark();
            String answer = chat.build().prompt(Demo.PROMPT).tools(tools).call().content();
            Demo.reportProxy(mark, answer);
        };
    }
}
