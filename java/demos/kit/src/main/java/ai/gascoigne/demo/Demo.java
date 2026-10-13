package ai.gascoigne.demo;

import ai.gascoigne.Result;
import ai.gascoigne.Stats;
import java.util.ArrayList;
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
        List<String> lines = IntStream.range(0, 400)
                .mapToObj(i -> LINE.formatted(i / 60, i % 60, i % 7, i, i % 90))
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
}
