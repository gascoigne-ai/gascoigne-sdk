package ai.gascoigne;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.File;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
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
    private static final String INSTALL_HINT = "mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne";
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
    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofMillis(500)).build();
    private final Object lock = new Object();
    private Boolean available;
    private int failures;
    private long pausedUntilNanos;
    private boolean warned;
    private Stats stats = new Stats(0, 0);

    private Gascoigne(Builder settings) {
        this.settings = settings;
    }

    private String baseUrl() {
        String addr = settings.addr != null ? settings.addr : System.getenv("GASCOIGNE_SERVER_ADDR");
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
            HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                return false;
            }
            Health health = JSON.readValue(response.body(), Health.class);
            if (health.proto() != PROTO) {
                warn("server speaks proto " + health.proto() + ", SDK " + PROTO + "; running without optimization");
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
            warn("gascoigne-cli not found on PATH; running without optimization. Install: " + INSTALL_HINT);
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
            warn("could not start gascoigne server (" + e.getMessage() + "); running without optimization");
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
                available = healthy() || startServer();
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
            HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                return Optional.empty();
            }
            return Optional.of(JSON.readValue(response.body(), Result.class)).filter(r -> r.text() != null);
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
        Optional<Result> result = post(OptimizeRequest.of(text, settings.agent, settings.session, attrs));
        if (result.isEmpty()) {
            recordFailure();
            return Result.unchanged(text);
        }
        synchronized (lock) {
            failures = 0;
            Result r = result.get();
            stats = new Stats(stats.rawTokens() + r.rawTokens(), stats.outTokens() + (r.outTokens() > 0 ? r.outTokens() : r.rawTokens()));
        }
        notifyObserver(text, result.get());
        return result.get();
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
        try {
            HttpRequest request = HttpRequest.newBuilder(URI.create(baseUrl() + "/sdk/v1/raw/" + rawId))
                    .timeout(settings.timeout)
                    .build();
            HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
            return response.statusCode() == 200 ? response.body() : "";
        } catch (IOException e) {
            recordFailure();
            return "";
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return "";
        }
    }

    /** Base URL that routes an LLM client through the gascoigne proxy; empty in bypass. */
    public Optional<String> proxyBaseUrl(String api) {
        if (!ready()) {
            return Optional.empty();
        }
        return Optional.of("openai".equals(api) ? baseUrl() + "/v1" : baseUrl());
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
