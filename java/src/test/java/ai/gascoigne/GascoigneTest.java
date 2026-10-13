package ai.gascoigne;

import static org.junit.jupiter.api.Assertions.*;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

class GascoigneTest {
    private static final String OPTIMIZE_REPLY =
            "{\"text\":\"short\",\"raw_id\":\"abc\",\"raw_tokens\":100,\"out_tokens\":5}";

    private HttpServer server;
    private final List<String> posts = new ArrayList<>();

    private String serve(int proto, int optimizeStatus) throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        String health = "{\"version\":\"t\",\"proto\":" + proto + "}";
        server.createContext("/sdk/v1/health", ex -> reply(ex, 200, health));
        server.createContext("/sdk/v1/optimize", ex -> {
            posts.add(new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            reply(ex, optimizeStatus, OPTIMIZE_REPLY);
        });
        server.createContext("/sdk/v1/raw/", ex -> reply(ex, 200, "original"));
        server.start();
        return "127.0.0.1:" + server.getAddress().getPort();
    }

    private static void reply(HttpExchange ex, int status, String body) throws IOException {
        byte[] b = body.getBytes(StandardCharsets.UTF_8);
        ex.sendResponseHeaders(status, b.length);
        ex.getResponseBody().write(b);
        ex.close();
    }

    @AfterEach void stop() { if (server != null) server.stop(0); }

    @Test void missingCliWarnsOnceAndPassesThrough() {
        var warnings = new ArrayList<String>();
        var g = Gascoigne.builder().addr("127.0.0.1:9").searchPath("").warn(warnings::add).build();
        assertEquals("hello", g.optimize("hello", Attrs.NONE));
        assertEquals("again", g.optimize("again", Attrs.NONE));
        assertTrue(g.proxyBaseUrl("openai").isEmpty());
        assertEquals("", g.raw("x"));
        assertEquals(1, warnings.stream().filter(w -> w.contains("not found on PATH")).count());
    }

    @Test void optimizesThroughServer() throws Exception {
        var seen = new ArrayList<String>();
        var g = Gascoigne.builder()
                .agent("demo")
                .addr(serve(1, 200))
                .onResult((original, result) -> seen.add(result.rawId()))
                .build();
        var res = g.optimizeResult("long ".repeat(100), Attrs.tool("grep"));
        assertEquals("short", res.text());
        assertEquals("abc", res.rawId());
        assertEquals(5, res.outTokens());
        assertTrue(posts.get(0).contains("\"agent\":\"demo\""));
        assertTrue(posts.get(0).contains("\"tool\":\"grep\""));
        assertEquals(List.of("abc"), seen);
        assertEquals(new Stats(100, 5), g.stats());
        assertTrue(g.proxyBaseUrl("openai").orElseThrow().endsWith("/v1"));
        assertEquals("original", g.raw("abc"));
    }

    @Test void unknownProtoBypasses() throws Exception {
        var g = Gascoigne.builder().addr(serve(99, 200)).searchPath("").warn(m -> {}).build();
        assertEquals("x", g.optimize("x", Attrs.NONE));
        assertTrue(posts.isEmpty());
    }

    @Test void failuresReturnInputAndOpenBreaker() throws Exception {
        var g = Gascoigne.builder().addr(serve(1, 500)).build();
        for (int i = 0; i < 7; i++) assertEquals("text", g.optimize("text", Attrs.NONE));
        assertEquals(5, posts.size());
    }

    @Test void wrapToolOptimizesStrings() throws Exception {
        var g = Gascoigne.builder().addr(serve(1, 200)).build();
        assertEquals("short", g.wrapTool("t", (String s) -> "big").apply("in"));
    }

    @Test void retrieveNarrowsTheOriginal() throws Exception {
        var g = Gascoigne.builder().addr(serve(1, 200)).build();
        // The stub serves "original" for every raw id: a single line.
        assertEquals("1: original", g.retrieve("abc", "", ""));
        assertEquals("", g.retrieve("abc", "nomatch", ""));
        assertTrue(g.retrieve("abc", "(", "").startsWith("Bad selection"));
    }
}
