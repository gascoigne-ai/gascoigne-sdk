package ai.gascoigne.spring;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;

import ai.gascoigne.Gascoigne;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.ai.chat.messages.Message;
import org.springframework.ai.chat.messages.ToolResponseMessage;
import org.springframework.ai.chat.messages.ToolResponseMessage.ToolResponse;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.model.tool.ToolCallingChatOptions;
import org.springframework.ai.model.tool.ToolCallingManager;
import org.springframework.ai.model.tool.ToolExecutionResult;
import org.springframework.ai.tool.definition.ToolDefinition;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

class GascoigneToolCallingManagerTest {
    private static final String BIG = "line of noisy log output\n".repeat(100);
    private static final String REPLY =
            "{\"text\":\"short [full: gascoigne raw abc]\",\"raw_id\":\"abc\","
                    + "\"raw_tokens\":100,\"out_tokens\":5}";

    private HttpServer server;
    private int optimizeCalls;

    @AfterEach
    void stop() {
        if (server != null) {
            server.stop(0);
        }
    }

    private Gascoigne gascoigne() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/sdk/v1/health", ex -> reply(ex, "{\"proto\":1}"));
        server.createContext("/sdk/v1/optimize", ex -> {
            optimizeCalls++;
            reply(ex, REPLY);
        });
        server.start();
        return Gascoigne.builder().addr("127.0.0.1:" + server.getAddress().getPort()).build();
    }

    private static void reply(HttpExchange ex, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        ex.sendResponseHeaders(200, bytes.length);
        ex.getResponseBody().write(bytes);
        ex.close();
    }

    /** A manager whose tools "returned" the given JSON data. */
    private static ToolCallingManager managerReturning(String tool, String responseData) {
        return new ToolCallingManager() {
            @Override
            public List<ToolDefinition> resolveToolDefinitions(ToolCallingChatOptions options) {
                return List.of();
            }

            @Override
            public ToolExecutionResult executeToolCalls(Prompt prompt, ChatResponse response) {
                ToolResponseMessage message =
                        new ToolResponseMessage(List.of(new ToolResponse("1", tool, responseData)));
                return ToolExecutionResult.builder()
                        .conversationHistory(List.<Message>of(message))
                        .build();
            }
        };
    }

    private static String dataOf(ToolExecutionResult result) {
        ToolResponseMessage message =
                assertInstanceOf(ToolResponseMessage.class, result.conversationHistory().get(0));
        return message.getResponses().get(0).responseData();
    }

    private ToolExecutionResult run(String tool, String data, Set<String> skip, int minChars)
            throws IOException {
        ToolCallingManager manager = new GascoigneToolCallingManager(
                managerReturning(tool, data), gascoigne(), skip, minChars);
        return manager.executeToolCalls(new Prompt("hi"), null);
    }

    @Test
    void stringResultsAreUnquotedShortenedAndQuotedAgain() throws IOException {
        String json = "\"" + BIG.replace("\n", "\\n") + "\"";
        String data = dataOf(run("search_logs", json, Set.of(), 800));
        assertEquals("\"short [full: gascoigne raw abc]\"", data);
    }

    @Test
    void skippedToolsSmallResultsAndAlreadyShortenedTextAreLeftAlone() throws IOException {
        String json = "\"" + BIG.replace("\n", "\\n") + "\"";
        assertEquals(json, dataOf(run("write_file", json, Set.of("write_file"), 800)));
        assertEquals(0, optimizeCalls);
        assertEquals("\"tiny\"", dataOf(run("search_logs", "\"tiny\"", Set.of(), 800)));
        assertEquals(0, optimizeCalls);
    }

    @Test
    void annotationWrapsTheManagerAndNothingElseDoes() {
        try (var enabled = new AnnotationConfigApplicationContext(Enabled.class);
                var plain = new AnnotationConfigApplicationContext(Plain.class)) {
            assertInstanceOf(
                    GascoigneToolCallingManager.class, enabled.getBean(ToolCallingManager.class));
            assertFalse(
                    plain.getBean(ToolCallingManager.class) instanceof GascoigneToolCallingManager);
        }
    }

    @Configuration
    @EnableGascoigne(skip = "write_file")
    static class Enabled {
        @Bean
        ToolCallingManager manager() {
            return managerReturning("t", "\"x\"");
        }
    }

    @Configuration
    static class Plain {
        @Bean
        ToolCallingManager manager() {
            return managerReturning("t", "\"x\"");
        }
    }
}
