using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.Net.Http.Json;
using System.Text.RegularExpressions;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Gascoigne;

/// <summary>
/// Finds the CLI, makes sure its server runs, and optimizes text through it. Every call is safe:
/// when the CLI is missing or the server misbehaves, inputs come back unchanged.
/// </summary>
public sealed class GascoigneClient : IDisposable
{
    private const int Proto = 1;
    private const string DefaultAddr = "127.0.0.1:7878";
    private const string InstallHint =
        "mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne";
    private const int BreakerFailures = 5;
    private static readonly TimeSpan BreakerPause = TimeSpan.FromSeconds(60);

    private static readonly JsonSerializerOptions RequestJson = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    private readonly GascoigneOptions _options;
    private readonly HttpClient _http;
    private readonly SemaphoreSlim _probe = new(1, 1);
    private readonly object _lock = new();
    private bool? _available;
    private int _failures;
    private DateTime _pausedUntil = DateTime.MinValue;
    private bool _warned;
    private Stats _stats;
    private NativeEngine? _engine;

    /// <summary>
    /// Creates a client; nothing is probed until the first call. In native mode the library is
    /// loaded here and a missing one throws <see cref="FileNotFoundException"/>.
    /// </summary>
    public GascoigneClient(GascoigneOptions? options = null)
    {
        _options = options ?? new GascoigneOptions();
        _http = new HttpClient { Timeout = _options.Timeout };
        _engine = OpenEngine(_options);
    }

    /// <summary>Releases the HTTP client and the embedded engine.</summary>
    public void Dispose()
    {
        _engine?.Dispose();
        _http.Dispose();
        _probe.Dispose();
    }

    private string BaseUrl
    {
        get
        {
            var addr = _options.Addr ?? Environment.GetEnvironmentVariable("GASCOIGNE_SERVER_ADDR");
            return "http://" + (string.IsNullOrEmpty(addr) ? DefaultAddr : addr);
        }
    }

    private static bool EnvIs(string name, string value) =>
        Environment.GetEnvironmentVariable(name) == value;

    private void Warn(string message)
    {
        lock (_lock)
        {
            if (_warned)
            {
                return;
            }

            _warned = true;
        }

        _options.Warn(message);
    }

    /// <summary>Opens the native engine when asked to; throws when no library is found.</summary>
    private static NativeEngine? OpenEngine(GascoigneOptions options)
    {
        var settings = options.Embedded
            ?? (EnvIs("GASCOIGNE_MODE", "native") ? new EmbeddedSettings() : null);
        return settings is null ? null : new NativeEngine(settings, options.Library);
    }

    private async Task<bool> HealthyAsync(CancellationToken ct)
    {
        try
        {
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
            timeout.CancelAfter(TimeSpan.FromMilliseconds(500));
            using var response = await _http.GetAsync($"{BaseUrl}/sdk/v1/health", timeout.Token);
            if (!response.IsSuccessStatusCode)
            {
                return false;
            }

            var health = await response.Content.ReadFromJsonAsync<Health>(timeout.Token);
            if (health?.Proto != Proto)
            {
                Warn($"server speaks proto {health?.Proto}, SDK {Proto}; "
                    + "running without optimization");
            }

            return health?.Proto == Proto;
        }
        catch (Exception e) when (IsTransient(e))
        {
            return false;
        }
    }

    private static bool IsTransient(Exception e) =>
        e is HttpRequestException
            or TaskCanceledException
            or JsonException
            or NotSupportedException
            or InvalidOperationException;

    private string? FindCli()
    {
        var bin = Environment.GetEnvironmentVariable("GASCOIGNE_BIN");
        if (_options.SearchPath is null && !string.IsNullOrEmpty(bin))
        {
            return bin;
        }

        var path = _options.SearchPath ?? Environment.GetEnvironmentVariable("PATH") ?? "";
        var name = OperatingSystem.IsWindows() ? "gascoigne.exe" : "gascoigne";
        return path.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries)
            .Select(dir => Path.Combine(dir, name))
            .FirstOrDefault(File.Exists);
    }

    private async Task<bool> StartServerAsync(CancellationToken ct)
    {
        var cli = FindCli();
        if (cli is null)
        {
            Warn("gascoigne-cli not found on PATH; running without optimization. "
                + $"Install: {InstallHint}");
            return false;
        }

        try
        {
            var start = new ProcessStartInfo(cli, "server start")
            {
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
            };
            using var process = Process.Start(start)!;
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
            timeout.CancelAfter(TimeSpan.FromSeconds(10));
            await process.WaitForExitAsync(timeout.Token);
        }
        catch (Exception e) when (e is Win32Exception or OperationCanceledException)
        {
            Warn($"could not start gascoigne server ({e.Message}); "
                + "running without optimization");
            return false;
        }

        return await AwaitHealthyAsync(ct);
    }

    private async Task<bool> AwaitHealthyAsync(CancellationToken ct)
    {
        var deadline = DateTime.UtcNow.AddSeconds(3);
        while (DateTime.UtcNow < deadline)
        {
            if (await HealthyAsync(ct))
            {
                return true;
            }

            await Task.Delay(100, ct);
        }

        Warn("gascoigne server did not come up; running without optimization");
        return false;
    }

    /// <summary>True when optimize calls will be tried. Probes once, then remembers.</summary>
    public async Task<bool> ReadyAsync(CancellationToken ct = default)
    {
        if (EnvIs("GASCOIGNE_SDK", "off") || EnvIs("GASCOIGNE_SERVER", "off"))
        {
            return false;
        }

        if (_available is null)
        {
            await _probe.WaitAsync(ct);
            try
            {
                _available ??= _engine is not null
                    || await HealthyAsync(ct)
                    || await StartServerAsync(ct);
            }
            finally
            {
                _probe.Release();
            }
        }

        return _available == true && DateTime.UtcNow >= _pausedUntil;
    }

    private void RecordFailure()
    {
        lock (_lock)
        {
            if (++_failures < BreakerFailures)
            {
                return;
            }

            _failures = 0;
            _pausedUntil = DateTime.UtcNow + BreakerPause;
        }
    }

    private void RecordSuccess(Result result)
    {
        lock (_lock)
        {
            _failures = 0;
            var after = result.OutTokens > 0 ? result.OutTokens : result.RawTokens;
            _stats = new Stats(_stats.RawTokens + result.RawTokens, _stats.OutTokens + after);
        }
    }

    /// <summary>Optimizes text; on any problem the result carries the input unchanged.</summary>
    public async Task<Result> OptimizeResultAsync(
        string text, Attrs? attrs = null, CancellationToken ct = default)
    {
        var unchanged = new Result(text);
        if (string.IsNullOrEmpty(text) || !await ReadyAsync(ct))
        {
            return unchanged;
        }

        var request = OptimizeRequest.From(text, _options, attrs);
        try
        {
            var result = await PostAsync(request, ct);
            if (result?.Text is null)
            {
                RecordFailure();
                return unchanged;
            }

            RecordSuccess(result);
            NotifyObserver(text, result);
            return result;
        }
        catch (Exception e) when (IsTransient(e))
        {
            RecordFailure();
            return unchanged;
        }
    }

    private async Task<Result?> PostAsync(OptimizeRequest request, CancellationToken ct)
    {
        if (_engine is { } engine)
        {
            var body = JsonSerializer.Serialize(request, RequestJson);
            return JsonSerializer.Deserialize<Result>(engine.Optimize(body));
        }

        using var response = await _http.PostAsJsonAsync(
            $"{BaseUrl}/sdk/v1/optimize", request, RequestJson, ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<Result>(ct);
    }

    private void NotifyObserver(string original, Result result)
    {
        try
        {
            _options.OnResult?.Invoke(original, result);
        }
        catch (Exception)
        {
            // An observer must never break the host app.
        }
    }

    /// <summary>Returns the text the model should read.</summary>
    public async Task<string> OptimizeAsync(
        string text, Attrs? attrs = null, CancellationToken ct = default) =>
        (await OptimizeResultAsync(text, attrs, ct)).Text;

    /// <summary>The original behind an optimized result; empty when unavailable.</summary>
    public async Task<string> RawAsync(string rawId, CancellationToken ct = default)
    {
        if (!await ReadyAsync(ct))
        {
            return "";
        }

        if (_engine is { } engine)
        {
            return TryRaw(engine, rawId);
        }

        try
        {
            var url = $"{BaseUrl}/sdk/v1/raw/{Uri.EscapeDataString(rawId)}";
            return await _http.GetStringAsync(url, ct);
        }
        catch (Exception e) when (IsTransient(e))
        {
            RecordFailure();
            return "";
        }
    }

    private static string TryRaw(NativeEngine engine, string rawId)
    {
        try
        {
            return engine.Raw(rawId);
        }
        catch (InvalidOperationException)
        {
            return "";
        }
    }

    /// <summary>Part of an original, for a model that needs what was folded.</summary>
    /// <param name="rawId">The id from a "gascoigne raw" hint.</param>
    /// <param name="grep">Regex matched per line; empty for all lines.</param>
    /// <param name="lines">Range such as "10-40"; empty for all lines.</param>
    /// <param name="ct">Cancellation.</param>
    public async Task<string> RetrieveAsync(
        string rawId, string grep = "", string lines = "", CancellationToken ct = default)
    {
        var original = await RawAsync(rawId, ct);
        if (original.Length == 0)
        {
            return $"No original stored for {rawId}.";
        }

        try
        {
            return Selection.Of(original, grep, lines);
        }
        catch (Exception e) when (e is FormatException
            or ArgumentException
            or RegexMatchTimeoutException)
        {
            return $"Bad selection: {e.Message}";
        }
    }

    /// <summary>
    /// Base URL that routes an LLM client through the gascoigne proxy, null in bypass.
    /// </summary>
    public async Task<string?> ProxyBaseUrlAsync(
        string api = "openai", CancellationToken ct = default)
    {
        // The embedded engine has no listening proxy.
        if (!await ReadyAsync(ct) || _engine is not null)
        {
            return null;
        }

        return api == "openai" ? $"{BaseUrl}/v1" : BaseUrl;
    }

    /// <summary>
    /// The recorded runs summed per group. Reads never throw and never trip the optimize breaker:
    /// on any failure (bypass, server down, a bad query) the answer is empty.
    /// </summary>
    public async Task<IReadOnlyList<Total>> TotalsAsync(
        TotalsQuery? query = null, CancellationToken ct = default)
    {
        query ??= new TotalsQuery();
        var fields = new Dictionary<string, string?>
        {
            ["by"] = query.By,
            ["session"] = query.Session,
            ["agent"] = query.Agent,
            ["model"] = query.Model,
            ["since"] = Rfc3339(query.Since),
        };
        return await ReadAsync<List<Total>>("/sdk/v1/stats", fields, (e, q) => e.Stats(q), ct)
            ?? [];
    }

    /// <summary>The recorded runs, newest first; empty on any failure.</summary>
    public async Task<IReadOnlyList<Run>> RunsAsync(
        RunsQuery? query = null, CancellationToken ct = default)
    {
        query ??= new RunsQuery();
        var fields = new Dictionary<string, string?>
        {
            ["session"] = query.Session,
            ["agent"] = query.Agent,
            ["model"] = query.Model,
            ["since"] = Rfc3339(query.Since),
            ["before"] = query.Before > 0
                ? query.Before.ToString(CultureInfo.InvariantCulture) : null,
            ["limit"] = query.Limit > 0 ? query.Limit.ToString(CultureInfo.InvariantCulture) : null,
        };
        return await ReadAsync<List<Run>>("/sdk/v1/recent", fields, (e, q) => e.Recent(q), ct)
            ?? [];
    }

    private static string? Rfc3339(DateTimeOffset? when) =>
        when?.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'", CultureInfo.InvariantCulture);

    /// <summary>A ledger read through the engine or the server; null on any failure.</summary>
    private async Task<T?> ReadAsync<T>(
        string path,
        Dictionary<string, string?> fields,
        Func<NativeEngine, string, string> viaEngine,
        CancellationToken ct)
        where T : class
    {
        var set = fields
            .Where(f => !string.IsNullOrEmpty(f.Value))
            .ToDictionary(f => f.Key, f => f.Value!);
        try
        {
            if (!await ReadyAsync(ct))
            {
                return null;
            }

            if (_engine is { } engine)
            {
                var doc = set.ToDictionary(
                    f => f.Key,
                    f => f.Key is "before" or "limit"
                        ? (object)long.Parse(f.Value, CultureInfo.InvariantCulture)
                        : f.Value);
                var answer = viaEngine(engine, JsonSerializer.Serialize(doc));
                return JsonSerializer.Deserialize<T>(answer);
            }

            var query = string.Join("&", set.Select(f => Uri.EscapeDataString(f.Key) + "="
                + Uri.EscapeDataString(f.Value).Replace("%20", "+", StringComparison.Ordinal)));
            var url = $"{BaseUrl}{path}{(query.Length > 0 ? "?" + query : "")}";
            using var response = await _http.GetAsync(url, ct);
            return response.IsSuccessStatusCode
                ? JsonSerializer.Deserialize<T>(await response.Content.ReadAsStringAsync(ct))
                : null;
        }
        catch (Exception e) when (e is HttpRequestException or TaskCanceledException
            or JsonException or InvalidOperationException or FormatException)
        {
            return null;
        }
    }

    /// <summary>Tokens (estimated) before and after, summed over this client's calls.</summary>
    public Stats Stats()
    {
        lock (_lock)
        {
            return _stats;
        }
    }

    /// <summary>Wraps a string-returning tool body, e.g. a Semantic Kernel function.</summary>
    public Func<TArg, Task<string>> WrapTool<TArg>(string name, Func<TArg, Task<string>> tool) =>
        async arg => await OptimizeAsync(await tool(arg), new Attrs { Tool = name });
}
