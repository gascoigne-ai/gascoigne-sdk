package ai.gascoigne;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.BiConsumer;
import java.util.function.Consumer;
import java.util.function.Function;

/**
 * Embeds gascoigne token optimization in agent frameworks.
 *
 * <p>Every call is safe: when the gascoigne CLI is missing or the server misbehaves, inputs come
 * back unchanged and no exception reaches the caller.
 */
public final class Gascoigne {
    private static final int PROTO = 1;
    private static final String DEFAULT_ADDR = "127.0.0.1:7878";
    private static final String INSTALL_HINT = "mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne";
    private static final int BREAKER_FAILURES = 5;
    private static final Duration BREAKER_PAUSE = Duration.ofSeconds(60);

    /** One optimize call: {@code text} is what the model should read. */
    public record Result(String text, String rawId, long rawTokens, long outTokens, String skipped) {
        static Result same(String text) { return new Result(text, "", 0, 0, ""); }
    }

    /** Where the text came from; null or empty fields are left out. */
    public record Attrs(String tool, String cmd, String url, String query, String model) {
        public static Attrs tool(String name) { return new Attrs(name, null, null, null, null); }
        public static final Attrs NONE = new Attrs(null, null, null, null, null);
    }

    public static final class Builder {
        private String agent = "";
        private String session = "";
        private Duration timeout = Duration.ofSeconds(5);
        private String addr;
        private String path;
        private BiConsumer<String, Result> onResult;
        private Consumer<String> warn = m -> System.err.println("[gascoigne] " + m);

        public Builder agent(String v) { agent = v; return this; }
        public Builder session(String v) { session = v; return this; }
        public Builder timeout(Duration v) { timeout = v; return this; }
        /** Sees (original, result) after each optimized call; exceptions in it are ignored. */
        public Builder onResult(BiConsumer<String, Result> v) { onResult = v; return this; }
        /** Server address, default {@code $GASCOIGNE_SERVER_ADDR} or 127.0.0.1:7878. */
        public Builder addr(String v) { addr = v; return this; }
        /** Where to look for the CLI instead of {@code $GASCOIGNE_BIN} and {@code $PATH}. */
        public Builder searchPath(String v) { path = v; return this; }
        public Builder warn(Consumer<String> v) { warn = v; return this; }
        public Gascoigne build() { return new Gascoigne(this); }
    }

    public static Builder builder() { return new Builder(); }

    private final Builder o;
    private final HttpClient http;
    private final Object lock = new Object();
    private Boolean ready;
    private int failures;
    private long pausedUntilNanos;
    private boolean warned;
    private final AtomicLong rawTokens = new AtomicLong();
    private final AtomicLong outTokens = new AtomicLong();

    private Gascoigne(Builder b) {
        this.o = b;
        this.http = HttpClient.newBuilder().connectTimeout(Duration.ofMillis(500)).build();
    }

    private String baseUrl() {
        String a = o.addr != null ? o.addr : System.getenv("GASCOIGNE_SERVER_ADDR");
        return "http://" + (a == null || a.isEmpty() ? DEFAULT_ADDR : a);
    }

    private static boolean env(String name, String value) { return value.equals(System.getenv(name)); }

    private void warn(String msg) {
        if (!warned) { warned = true; o.warn.accept(msg); }
    }

    private boolean healthy() {
        try {
            var req = HttpRequest.newBuilder(URI.create(baseUrl() + "/sdk/v1/health")).timeout(Duration.ofMillis(500)).build();
            var resp = http.send(req, HttpResponse.BodyHandlers.ofString());
            if (resp.statusCode() != 200) return false;
            var m = Json.decode(resp.body());
            if (m == null) return false;
            if (!String.valueOf(PROTO).equals(m.get("proto"))) {
                warn("server speaks proto " + m.get("proto") + ", SDK " + PROTO + "; running without optimization");
                return false;
            }
            return true;
        } catch (IOException e) {
            return false;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        }
    }

    private Optional<Path> findCli() {
        String bin = System.getenv("GASCOIGNE_BIN");
        if (o.path == null && bin != null && !bin.isEmpty()) return Optional.of(Path.of(bin));
        String path = o.path != null ? o.path : System.getenv("PATH");
        if (path == null) return Optional.empty();
        for (String dir : path.split(java.io.File.pathSeparator)) {
            if (dir.isEmpty()) continue;
            Path p = Path.of(dir, "gascoigne");
            if (Files.isExecutable(p) && !Files.isDirectory(p)) return Optional.of(p);
        }
        return Optional.empty();
    }

    private boolean startServer() {
        var exe = findCli();
        if (exe.isEmpty()) {
            warn("gascoigne-cli not found on PATH; running without optimization. Install: " + INSTALL_HINT);
            return false;
        }
        try {
            var p = new ProcessBuilder(exe.get().toString(), "server", "start")
                .redirectErrorStream(true).redirectOutput(ProcessBuilder.Redirect.DISCARD).start();
            if (!p.waitFor(10, TimeUnit.SECONDS)) p.destroyForcibly();
        } catch (IOException e) {
            warn("could not start gascoigne server (" + e.getMessage() + "); running without optimization");
            return false;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        }
        long end = System.nanoTime() + TimeUnit.SECONDS.toNanos(3);
        while (System.nanoTime() < end) {
            if (healthy()) return true;
            try { Thread.sleep(100); } catch (InterruptedException e) { Thread.currentThread().interrupt(); return false; }
        }
        warn("gascoigne server did not come up; running without optimization");
        return false;
    }

    /** True when optimize calls will be tried. Probes once, then remembers. */
    public boolean ready() {
        if (env("GASCOIGNE_SDK", "off") || env("GASCOIGNE_SERVER", "off")) return false;
        synchronized (lock) {
            if (ready == null) ready = healthy() || startServer();
            return ready && System.nanoTime() >= pausedUntilNanos;
        }
    }

    private void failed() {
        synchronized (lock) {
            if (++failures >= BREAKER_FAILURES) {
                failures = 0;
                pausedUntilNanos = System.nanoTime() + BREAKER_PAUSE.toNanos();
            }
        }
    }

    /** Optimizes {@code text}; on any problem the result carries the input unchanged. */
    public Result optimizeResult(String text, Attrs attrs) {
        if (text == null || text.isEmpty() || !ready()) return Result.same(text);
        var body = new LinkedHashMap<String, String>();
        body.put("text", text);
        put(body, "agent", o.agent);
        put(body, "session", o.session);
        if (attrs != null) {
            put(body, "tool", attrs.tool());
            put(body, "cmd", attrs.cmd());
            put(body, "url", attrs.url());
            put(body, "query", attrs.query());
            put(body, "model", attrs.model());
        }
        try {
            var req = HttpRequest.newBuilder(URI.create(baseUrl() + "/sdk/v1/optimize")).timeout(o.timeout)
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(Json.encode(body))).build();
            var resp = http.send(req, HttpResponse.BodyHandlers.ofString());
            var m = resp.statusCode() == 200 ? Json.decode(resp.body()) : null;
            if (m == null || !m.containsKey("text")) { failed(); return Result.same(text); }
            var res = new Result(m.get("text"), m.getOrDefault("raw_id", ""), num(m.get("raw_tokens")),
                num(m.get("out_tokens")), m.getOrDefault("skipped", ""));
            synchronized (lock) { failures = 0; }
            rawTokens.addAndGet(res.rawTokens());
            outTokens.addAndGet(res.outTokens() > 0 ? res.outTokens() : res.rawTokens());
            if (o.onResult != null) {
                try { o.onResult.accept(text, res); } catch (RuntimeException ignored) { /* observer must not break the app */ }
            }
            return res;
        } catch (IOException | RuntimeException e) {
            failed();
            return Result.same(text);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return Result.same(text);
        }
    }

    private static void put(Map<String, String> m, String k, String v) {
        if (v != null && !v.isEmpty()) m.put(k, v);
    }

    private static long num(String s) {
        try { return s == null ? 0 : Long.parseLong(s); } catch (NumberFormatException e) { return 0; }
    }

    public String optimize(String text, Attrs attrs) { return optimizeResult(text, attrs).text(); }

    /** The original behind an optimized result; empty when unavailable. */
    public String raw(String rawId) {
        if (!ready()) return "";
        try {
            var req = HttpRequest.newBuilder(URI.create(baseUrl() + "/sdk/v1/raw/" + rawId)).timeout(o.timeout).build();
            var resp = http.send(req, HttpResponse.BodyHandlers.ofString());
            return resp.statusCode() == 200 ? resp.body() : "";
        } catch (IOException | RuntimeException e) {
            failed();
            return "";
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return "";
        }
    }

    /** Base URL that routes an LLM client through the gascoigne proxy, empty in bypass. */
    public Optional<String> proxyBaseUrl(String api) {
        if (!ready()) return Optional.empty();
        return Optional.of("openai".equals(api) ? baseUrl() + "/v1" : baseUrl());
    }

    /** Tokens (estimated) before and after, summed over this instance's calls. */
    public long[] stats() { return new long[] {rawTokens.get(), outTokens.get()}; }

    /** Wraps a string-returning tool function, e.g. a LangChain4j or Spring AI tool body. */
    public <A> Function<A, String> wrapTool(String name, Function<A, String> fn) {
        return a -> optimize(fn.apply(a), Attrs.tool(name));
    }
}
