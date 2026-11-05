package ai.gascoigne;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.File;
import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.TimeUnit;
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
    private static final String INSTALL_HINT =
            "mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne";
    private static final int BREAKER_FAILURES = 5;
    private static final Duration BREAKER_PAUSE = Duration.ofSeconds(60);
    private static final ObjectMapper JSON = new ObjectMapper();

    /** Settings; the defaults work. */
    public static final class Builder {
        private String agent = "";
        private String session = "";
        private Duration timeout = Duration.ofSeconds(5);
        private String addr;
        private String searchPath;
        private Settings embedded;
        private String library;
        private BiConsumer<String, Result> onResult = (original, result) -> {};
        private Consumer<String> warn = message -> System.err.println("[gascoigne] " + message);

        /** Agent or framework name, for per-agent stats. */
        public Builder agent(String agent) {
            this.agent = agent;
            return this;
        }

        /** Session id, for per-session stats. */
        public Builder session(String session) {
            this.session = session;
            return this;
        }

        /** Per-call timeout, default 5 s. */
        public Builder timeout(Duration timeout) {
            this.timeout = timeout;
            return this;
        }

        /** Server address, default {@code $GASCOIGNE_SERVER_ADDR} or 127.0.0.1:7878. */
        public Builder addr(String addr) {
            this.addr = addr;
            return this;
        }

        /** Where to look for the CLI instead of {@code $GASCOIGNE_BIN} and {@code $PATH}. */
        public Builder searchPath(String searchPath) {
            this.searchPath = searchPath;
            return this;
        }

        /**
         * Runs the engine in this process through libgascoigne (needs JNA on the class path)
         * instead of the server; {@code settings} is merged by the library.
         * {@link #build()} throws {@link IllegalStateException} when no library is found.
         * See spec/native.md.
         */
        public Builder embedded(Settings settings) {
            this.embedded = settings;
            return this;
        }

        /** Path of libgascoigne for embedded mode, instead of {@code $GASCOIGNE_LIB}. */
        public Builder library(String path) {
            this.library = path;
            return this;
        }

        /** Sees (original, result) after each optimized call; exceptions in it are ignored. */
        public Builder onResult(BiConsumer<String, Result> onResult) {
            this.onResult = onResult;
            return this;
        }

        /** Where the one-time warnings go. */
        public Builder warn(Consumer<String> warn) {
            this.warn = warn;
            return this;
        }

        public Gascoigne build() {
            return new Gascoigne(this);
        }
    }

    public static Builder builder() {
        return new Builder();
    }

    private final Builder settings;
    private final HttpClient http =
            HttpClient.newBuilder().connectTimeout(Duration.ofMillis(500)).build();
    private final Object lock = new Object();
    private Boolean available;
    private int failures;
    private long pausedUntilNanos;
    private boolean warned;
    private Stats stats = new Stats(0, 0);
    private NativeEngine engine;

    private Gascoigne(Builder settings) {
        this.settings = settings;
        this.engine = openEngine();
    }

    /** Settings for embedded mode: the builder's, else defaults when GASCOIGNE_MODE asks. */
    private Settings embeddedSettings() {
        if (settings.embedded != null) {
            return settings.embedded;
        }
        return envIs("GASCOIGNE_MODE", "native") ? Settings.defaults() : null;
    }

    /**
     * Opens the native engine when asked to.
     *
     * @throws IllegalStateException when native mode is asked for and no library can be loaded
     */
    private NativeEngine openEngine() {
        Settings wanted = embeddedSettings();
        if (wanted == null) {
            return null;
        }
        try {
            return new NativeEngine(wanted, settings.library);
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception | LinkageError e) {
            throw new IllegalStateException("native gascoigne unavailable: " + e, e);
        }
    }

    /** Releases the embedded engine, if any. */
    public void close() {
        synchronized (lock) {
            if (engine != null) {
                engine.close();
                engine = null;
                available = false;
            }
        }
    }

    private String baseUrl() {
        String addr =
                settings.addr != null ? settings.addr : System.getenv("GASCOIGNE_SERVER_ADDR");
        return "http://" + (addr == null || addr.isEmpty() ? DEFAULT_ADDR : addr);
    }

    private static boolean envIs(String name, String value) {
        return value.equals(System.getenv(name));
    }

    private void warn(String message) {
        synchronized (lock) {
            if (warned) {
                return;
            }
            warned = true;
        }
        settings.warn.accept(message);
    }

    private boolean healthy() {
        try {
            HttpRequest request = HttpRequest.newBuilder(URI.create(baseUrl() + "/sdk/v1/health"))
                    .timeout(Duration.ofMillis(500))
                    .build();
            HttpResponse<String> response =
                    http.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                return false;
            }
            Health health = JSON.readValue(response.body(), Health.class);
            if (health.proto() != PROTO) {
                warn("server speaks proto " + health.proto() + ", SDK " + PROTO
                        + "; running without optimization");
            }
            return health.proto() == PROTO;
        } catch (IOException e) {
            return false;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        }
    }

    private Optional<Path> findCli() {
        String bin = System.getenv("GASCOIGNE_BIN");
        if (settings.searchPath == null && bin != null && !bin.isEmpty()) {
            return Optional.of(Path.of(bin));
        }
        String path = settings.searchPath != null ? settings.searchPath : System.getenv("PATH");
        if (path == null) {
            return Optional.empty();
        }
        for (String dir : path.split(File.pathSeparator)) {
            Path candidate = Path.of(dir, "gascoigne");
            if (!dir.isEmpty() && Files.isExecutable(candidate) && !Files.isDirectory(candidate)) {
                return Optional.of(candidate);
            }
        }
        return Optional.empty();
    }

    private boolean startServer() {
        Optional<Path> cli = findCli();
        if (cli.isEmpty()) {
            warn("gascoigne-cli not found on PATH; running without optimization. Install: "
                    + INSTALL_HINT);
            return false;
        }
        try {
            Process process = new ProcessBuilder(cli.get().toString(), "server", "start")
                    .redirectErrorStream(true)
                    .redirectOutput(ProcessBuilder.Redirect.DISCARD)
                    .start();
            if (!process.waitFor(10, TimeUnit.SECONDS)) {
                process.destroyForcibly();
            }
        } catch (IOException e) {
            warn("could not start gascoigne server (" + e.getMessage()
                    + "); running without optimization");
            return false;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        }
        return awaitHealthy();
    }

    private boolean awaitHealthy() {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(3);
        while (System.nanoTime() < deadline) {
            if (healthy()) {
                return true;
            }
            try {
                Thread.sleep(100);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return false;
            }
        }
        warn("gascoigne server did not come up; running without optimization");
        return false;
    }

    /** True when optimize calls will be tried. Probes once, then remembers. */
    public boolean ready() {
        if (envIs("GASCOIGNE_SDK", "off") || envIs("GASCOIGNE_SERVER", "off")) {
            return false;
        }
        synchronized (lock) {
            if (available == null) {
                available = engine != null || healthy() || startServer();
            }
            return available && System.nanoTime() >= pausedUntilNanos;
        }
    }

    private void recordFailure() {
        synchronized (lock) {
            if (++failures >= BREAKER_FAILURES) {
                failures = 0;
                pausedUntilNanos = System.nanoTime() + BREAKER_PAUSE.toNanos();
            }
        }
    }

    private Optional<Result> post(OptimizeRequest body) {
        try {
            HttpRequest request = HttpRequest.newBuilder(URI.create(baseUrl() + "/sdk/v1/optimize"))
                    .timeout(settings.timeout)
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(JSON.writeValueAsString(body)))
                    .build();
            HttpResponse<String> response =
                    http.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                return Optional.empty();
            }
            Result result = JSON.readValue(response.body(), Result.class);
            return Optional.of(result).filter(r -> r.text() != null);
        } catch (JsonProcessingException e) {
            return Optional.empty();
        } catch (IOException e) {
            return Optional.empty();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return Optional.empty();
        }
    }

    /** Optimizes {@code text}; on any problem the result carries the input unchanged. */
    public Result optimizeResult(String text, Attrs attrs) {
        if (text == null || text.isEmpty() || !ready()) {
            return Result.unchanged(text);
        }
        OptimizeRequest body = OptimizeRequest.of(text, settings.agent, settings.session, attrs);
        Optional<Result> result = engine != null ? embeddedCall(body) : post(body);
        if (result.isEmpty()) {
            recordFailure();
            return Result.unchanged(text);
        }
        synchronized (lock) {
            failures = 0;
            Result r = result.get();
            long out = r.outTokens() > 0 ? r.outTokens() : r.rawTokens();
            stats = new Stats(stats.rawTokens() + r.rawTokens(), stats.outTokens() + out);
        }
        notifyObserver(text, result.get());
        return result.get();
    }

    private Optional<Result> embeddedCall(OptimizeRequest body) {
        try {
            return Optional.of(engine.optimize(body)).filter(r -> r.text() != null);
        } catch (Exception e) {
            return Optional.empty();
        }
    }

    private void notifyObserver(String original, Result result) {
        try {
            settings.onResult.accept(original, result);
        } catch (RuntimeException ignored) {
            // an observer must never break the host app
        }
    }

    /** The text the model should read. */
    public String optimize(String text, Attrs attrs) {
        return optimizeResult(text, attrs).text();
    }

    /** The original behind an optimized result; empty when unavailable. */
    public String raw(String rawId) {
        if (!ready()) {
            return "";
        }
        if (engine != null) {
            return engine.raw(rawId);
        }
        try {
            URI uri = URI.create(baseUrl() + "/sdk/v1/raw/" + rawId);
            HttpRequest request = HttpRequest.newBuilder(uri)
                    .timeout(settings.timeout)
                    .build();
            HttpResponse<String> response =
                    http.send(request, HttpResponse.BodyHandlers.ofString());
            return response.statusCode() == 200 ? response.body() : "";
        } catch (IOException e) {
            recordFailure();
            return "";
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return "";
        }
    }

    /**
     * Part of an original, for a model that needs what was folded.
     *
     * @param rawId the id from a "gascoigne raw" hint
     * @param grep regex matched per line, empty for all lines
     * @param lines range such as "10-40", empty for all lines
     */
    public String retrieve(String rawId, String grep, String lines) {
        String original = raw(rawId);
        if (original.isEmpty()) {
            return "No original stored for " + rawId + ".";
        }
        try {
            return Selection.of(original, grep, lines);
        } catch (RuntimeException e) {
            return "Bad selection: " + e.getMessage();
        }
    }

    /** Base URL that routes an LLM client through the gascoigne proxy; empty in bypass. */
    public Optional<String> proxyBaseUrl(String api) {
        // The embedded engine has no listening proxy.
        if (!ready() || engine != null) {
            return Optional.empty();
        }
        return Optional.of("openai".equals(api) ? baseUrl() + "/v1" : baseUrl());
    }

    /**
     * The recorded runs summed per group. Reads never throw and never trip the optimize breaker:
     * on any failure (bypass, server down, a bad query) the answer is empty.
     */
    public List<Total> totals(TotalsQuery query) {
        Map<String, String> params = new LinkedHashMap<>();
        put(params, "by", query.by());
        put(params, "session", query.session());
        put(params, "agent", query.agent());
        put(params, "model", query.model());
        put(params, "since", seconds(query.since()));
        return read("/sdk/v1/stats", params, new TypeReference<List<Total>>() {}, List.of(),
                engineQuery -> engine.stats(engineQuery));
    }

    /** The recorded runs, newest first; empty on any failure. */
    public List<Run> runs(RunsQuery query) {
        Map<String, String> params = new LinkedHashMap<>();
        put(params, "session", query.session());
        put(params, "agent", query.agent());
        put(params, "model", query.model());
        put(params, "since", seconds(query.since()));
        put(params, "before", query.before() > 0 ? Long.toString(query.before()) : null);
        put(params, "limit", query.limit() > 0 ? Integer.toString(query.limit()) : null);
        return read("/sdk/v1/recent", params, new TypeReference<List<Run>>() {}, List.of(),
                engineQuery -> engine.recent(engineQuery));
    }

    /** RFC 3339 to the second, null for none. */
    private static String seconds(java.time.Instant when) {
        return when == null ? null : when.truncatedTo(ChronoUnit.SECONDS).toString();
    }

    private static void put(Map<String, String> params, String key, String value) {
        if (value != null && !value.isEmpty()) {
            params.put(key, value);
        }
    }

    /** A ledger read through the engine or the server; the fallback on any failure. */
    private <T> T read(String path, Map<String, String> params, TypeReference<T> type, T fallback,
            java.util.function.Function<String, String> viaEngine) {
        if (!ready()) {
            return fallback;
        }
        try {
            if (engine != null) {
                Map<String, Object> doc = new LinkedHashMap<>(params);
                for (String number : List.of("before", "limit")) {
                    if (params.containsKey(number)) {
                        doc.put(number, Long.parseLong(params.get(number)));
                    }
                }
                return JSON.readValue(viaEngine.apply(JSON.writeValueAsString(doc)), type);
            }
            StringBuilder url = new StringBuilder(baseUrl()).append(path);
            String separator = "?";
            for (var entry : params.entrySet()) {
                url.append(separator)
                        .append(URLEncoder.encode(entry.getKey(), StandardCharsets.UTF_8))
                        .append('=')
                        .append(URLEncoder.encode(entry.getValue(), StandardCharsets.UTF_8));
                separator = "&";
            }
            HttpRequest request = HttpRequest.newBuilder(URI.create(url.toString()))
                    .timeout(settings.timeout)
                    .build();
            HttpResponse<String> response =
                    http.send(request, HttpResponse.BodyHandlers.ofString());
            return response.statusCode() == 200 ? JSON.readValue(response.body(), type) : fallback;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return fallback;
        } catch (IOException | RuntimeException e) {
            return fallback;
        }
    }

    /** Tokens (estimated) before and after, summed over this instance's calls. */
    public Stats stats() {
        synchronized (lock) {
            return stats;
        }
    }

    /** Wraps a string-returning tool function, e.g. a LangChain4j or Spring AI tool body. */
    public <A> Function<A, String> wrapTool(String name, Function<A, String> tool) {
        Attrs attrs = Attrs.tool(name);
        return arg -> optimize(tool.apply(arg), attrs);
    }
}
