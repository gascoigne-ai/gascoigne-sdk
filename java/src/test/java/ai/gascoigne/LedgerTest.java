package ai.gascoigne;

import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class LedgerTest {
    private static final Path LIB = Path.of("../native/dist/libgascoigne.so").toAbsolutePath();
    private static final String TOTALS = "[{\"group\":\"sdk\",\"runs\":2,\"optimized\":2,"
            + "\"failed\":0,\"raw_tokens\":100,\"out_tokens\":40,\"saved\":60}]";
    private static final String RUNS = "[{\"id\":7,\"time\":\"2026-11-01T10:00:00Z\","
            + "\"session\":\"s1\",\"raw_tokens\":100,\"out_tokens\":10,\"raw_id\":\"abc\","
            + "\"outcome\":\"optimized\",\"optimizers\":[\"log\"]}]";
    private static final String COSTS = "{\"billing\":\"api\",\"first_read_usd\":0.5,"
            + "\"in_context_usd\":1.5,\"rereads\":110,\"savings\":[{\"model\":\"m\","
            + "\"source\":\"static\",\"tokenizer\":\"o200k\",\"tokens\":10,\"model_tokens\":10,"
            + "\"first_read_usd\":0.5,\"in_context_usd\":1.5}]}";

    private HttpServer server;
    private final List<String> urls = new ArrayList<>();

    private String serve(int status) throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        String health = "{\"version\":\"t\",\"proto\":1}";
        server.createContext("/sdk/v1/health", ex -> reply(ex, 200, health));
        var routes =
                Map.of("/sdk/v1/stats", TOTALS, "/sdk/v1/recent", RUNS, "/sdk/v1/costs", COSTS);
        for (var route : routes.entrySet()) {
            server.createContext(route.getKey(), ex -> {
                urls.add(ex.getRequestURI().toString());
                reply(ex, status, status == 200 ? route.getValue() : "boom");
            });
        }
        server.start();
        return "127.0.0.1:" + server.getAddress().getPort();
    }

    private static void reply(HttpExchange ex, int status, String body) throws IOException {
        byte[] b = body.getBytes(StandardCharsets.UTF_8);
        ex.sendResponseHeaders(status, b.length);
        ex.getResponseBody().write(b);
        ex.close();
    }

    /** The order of query parameters is not part of the contract. */
    private static void assertSameQuery(String expected, String actual) {
        assertEquals(path(expected), path(actual));
        assertEquals(params(expected), params(actual));
    }

    private static String path(String target) {
        return target.substring(0, target.indexOf('?'));
    }

    private static java.util.Set<String> params(String target) {
        String query = target.substring(target.indexOf('?') + 1);
        return new java.util.TreeSet<>(List.of(query.split("&")));
    }

    @AfterEach void stop() { if (server != null) server.stop(0); }

    @Test void readsThroughTheServer() throws Exception {
        var g = Gascoigne.builder().addr(serve(200)).build();
        var totals = g.totals(TotalsQuery.builder().by("agent").session("s 1")
                .since(Instant.parse("2026-11-01T00:00:00Z")).build());
        assertEquals(1, totals.size());
        assertEquals(new Total("sdk", 2, 2, 0, 100, 40, 60, "", ""), totals.get(0));
        assertSameQuery(
                "/sdk/v1/stats?by=agent&session=s+1&since=2026-11-01T00%3A00%3A00Z", urls.get(0));
        var runs = g.runs(RunsQuery.builder().session("s1").limit(5).before(9).build());
        assertEquals(7, runs.get(0).id());
        assertEquals("abc", runs.get(0).rawId());
        assertEquals(List.of("log"), runs.get(0).optimizers());
        assertSameQuery(
                "/sdk/v1/recent?before=9&limit=5&session=s1", urls.get(1));
        var costs = g.costs(TotalsQuery.ALL);
        assertEquals("api", costs.billing());
        assertEquals(1.5, costs.inContextUsd());
        assertEquals("static", costs.savings().get(0).source());
    }

    @Test void failuresAreEmptyNotExceptionsAndKeepTheBreakerClosed() throws Exception {
        var g = Gascoigne.builder().addr(serve(500)).build();
        for (int i = 0; i < 10; i++) {
            assertTrue(g.totals(TotalsQuery.ALL).isEmpty());
        }
        assertTrue(g.runs(RunsQuery.ALL).isEmpty());
        assertEquals("", g.costs(TotalsQuery.ALL).billing());
        assertTrue(g.ready());
    }

    @Test void bypassIsEmpty() {
        var g = Gascoigne.builder().addr("127.0.0.1:9").searchPath("").warn(m -> {}).build();
        assertTrue(g.totals(TotalsQuery.ALL).isEmpty());
        assertTrue(g.costs(TotalsQuery.ALL).savings().isEmpty());
    }

    @Test void settingsCarryLedgerAndPricing() throws Exception {
        var settings = Settings.defaults().withLedger("memory").withPricing(new Pricing(
                "subscription", Map.of("m", new Price(1.0, 2.0, null, null, null)), null));
        var json = new com.fasterxml.jackson.databind.ObjectMapper().readTree(
                new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(settings));
        assertEquals("memory", json.get("ledger").asText());
        assertEquals("subscription", json.get("pricing").get("billing").asText());
        assertEquals(1.0, json.get("pricing").get("prices").get("m").get("in").asDouble());
        assertFalse(json.get("pricing").has("file"));
        assertFalse(json.has("config"));
    }

    @Test void embeddedMemoryLedger(@TempDir Path dir) throws Exception {
        assumeTrue(Files.exists(LIB), "build native/ first");
        var settings = Settings.defaults().withoutUserFile().withLedger("memory").withPricing(
                new Pricing(
                        null,
                        Map.of("acme-large", new Price(3.0, 15.0, null, null, "claude")),
                        null));
        var g = Gascoigne.builder().agent("sdk").session("s1").embedded(settings)
                .library(LIB.toString()).build();
        String raw = "INFO request served path=/api/items status=200 ms=12\n".repeat(400);
        g.optimizeResult(raw, new Attrs("bash", "tail app.log", "", "", "acme-large"));
        var totals = g.totals(TotalsQuery.builder().by("agent").build());
        assertEquals("sdk", totals.get(0).group());
        assertEquals(1, totals.get(0).runs());
        assertTrue(totals.get(0).saved() > 0);
        var runs = g.runs(RunsQuery.builder().session("s1").build());
        assertEquals(1, runs.size());
        assertFalse(runs.get(0).rawId().isEmpty());
        var costs = g.costs(TotalsQuery.ALL);
        assertTrue(costs.inContextUsd() > 0);
        assertEquals("static", costs.savings().get(0).source());
        assertTrue(g.totals(TotalsQuery.builder().by("nonsense").build()).isEmpty());
        g.close();
    }
}
