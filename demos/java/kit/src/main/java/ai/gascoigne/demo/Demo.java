package ai.gascoigne.demo;

import ai.gascoigne.Result;
import ai.gascoigne.Stats;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

/** The noisy tool and the before/after report shared by the Java demos. */
public final class Demo {
    /** What every demo asks. */
    public static final String PROMPT =
            "Call the search_logs tool once, then tell me in one sentence what went wrong "
                    + "and for how long.";

    private static final String LINE =
            "2026-10-13T12:%02d:%02dZ INFO worker-%d handled request id=%d status=200 took=%dms";
    private static final String ERROR_LINE =
            "2026-10-13T12:04:10Z ERROR db connection timeout after 30s (pool exhausted)";

    private static String before = "";
    private static Result last;

    private Demo() {}

    /** True for a run without LLM calls. */
    public static boolean dry() {
        String env = System.getenv("GASCOIGNE_DEMO_DRY");
        return "1".equals(env != null ? env : System.getProperty("GASCOIGNE_DEMO_DRY"));
    }

    /** The noisy tool: 400 near-identical lines and one error. */
    public static String noisyLogs() {
        // Request ids differ per call, as in real logs; the proxy caches identical results.
        long firstId = java.util.concurrent.ThreadLocalRandom.current().nextInt(900_000);
        List<String> lines = IntStream.range(0, 400)
                .mapToObj(i -> LINE.formatted(i / 60, i % 60, i % 7, firstId + i, i % 90))
                .collect(Collectors.toCollection(ArrayList::new));
        lines.add(250, ERROR_LINE);
        return String.join("\n", lines);
    }

    /** An {@code onResult} hook that remembers the last call for {@link #report}. */
    public static void observe(String original, Result result) {
        before = original;
        last = result;
    }

    /** Prints the answer (if any) and what gascoigne saved. */
    public static void report(Stats stats, String answer) {
        if (answer != null && !answer.isBlank()) {
            System.out.printf("Model answer:%n%s%n%n", indent(answer.strip()));
        }
        if (last == null) {
            System.out.println("No optimization happened. Is the gascoigne CLI on PATH?");
            System.out.println("Install: mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/"
                    + "gascoigne");
            return;
        }
        System.out.printf("Tool result: %,d tokens%n%s%n%n", last.rawTokens(), preview(before));
        System.out.printf(
                "Model reads: %,d tokens%n%s%n%n", last.outTokens(), preview(last.text()));
        System.out.printf("Saved %.0f%%: %,d -> %,d tokens.%n", stats.saved() * 100,
                stats.rawTokens(), stats.outTokens());
        System.out.printf("Original: gascoigne raw %s%n", last.rawId());
    }

    /** The first lines of a text, each cut to the display width. */
    private static String preview(String text) {
        List<String> rows =
                text.lines().map(row -> row.substring(0, Math.min(row.length(), 72))).toList();
        List<String> shown = new ArrayList<>(rows.subList(0, Math.min(rows.size(), 8)));
        if (rows.size() > 8) {
            shown.add("... " + (rows.size() - 8) + " more lines");
        }
        return indent(String.join("\n", shown));
    }

    private static String indent(String text) {
        return "  " + text.replace("\n", "\n  ");
    }

    // ---- proxy mode ------------------------------------------------------------------------

    private static final ObjectMapper JSON = new ObjectMapper();

    /** Events the gascoigne server recorded after id {@code after}, oldest first. */
    private static List<ProxyEvent> proxyEvents(long after) {
        String addr = System.getenv().getOrDefault("GASCOIGNE_SERVER_ADDR", "127.0.0.1:7878");
        try {
            URI uri = URI.create("http://" + addr + "/api/events?after=" + after + "&limit=200");
            HttpRequest request = HttpRequest.newBuilder(uri).build();
            HttpResponse<String> response =
                    HttpClient.newHttpClient().send(request, HttpResponse.BodyHandlers.ofString());
            ProxyEvent[] events = JSON.readValue(response.body(), ProxyEvent[].class);
            return java.util.Arrays.stream(events)
                    .filter(e -> "proxy".equals(e.pipeline()))
                    .sorted(Comparator.comparingLong(ProxyEvent::id))
                    .toList();
        } catch (IOException e) {
            return List.of();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return List.of();
        }
    }

    /** Id of the newest proxy event; pass it to {@link #reportProxy} after the agent ran. */
    public static long proxyMark() {
        return proxyEvents(0).stream().mapToLong(ProxyEvent::id).max().orElse(0);
    }

    /** Prints the answer and the tool results the gascoigne proxy shortened since {@code mark}. */
    public static void reportProxy(long mark, String answer) {
        System.out.printf("Model answer:%n%s%n%n", indent(answer.strip()));
        List<ProxyEvent> results = List.of();
        for (int attempt = 0; attempt < 10 && results.isEmpty(); attempt++) {
            results = proxyEvents(mark).stream()
                    .filter(e -> e.rawTokens() > 0 && "default".equals(e.route()))
                    .toList();
            if (results.isEmpty()) {
                try {
                    Thread.sleep(200);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    return;
                }
            }
        }
        if (results.isEmpty()) {
            System.out.println("The proxy saw no new tool result. Is the gascoigne CLI on PATH?");
            return;
        }
        System.out.println("Tool results shortened by the proxy:");
        for (ProxyEvent e : results) {
            long saved = Math.round((1 - (double) e.outTokens() / e.rawTokens()) * 100);
            System.out.printf("  %s: %,d -> %,d tokens (saved %d%%)%n", e.command(), e.rawTokens(),
                    e.outTokens(), saved);
            System.out.printf("  Original: gascoigne raw %s%n", e.rawId());
        }
    }
}
