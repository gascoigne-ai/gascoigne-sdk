using System.ComponentModel;
using System.Diagnostics;
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

    /// <summary>Creates a client; nothing is probed until the first call.</summary>
    public GascoigneClient(GascoigneOptions? options = null)
    {
        _options = options ?? new GascoigneOptions();
        _http = new HttpClient { Timeout = _options.Timeout };
    }

    /// <summary>Releases the HTTP client.</summary>
    public void Dispose()
    {
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
            or NotSupportedException;

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
                _available ??= await HealthyAsync(ct) || await StartServerAsync(ct);
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
            using var response = await _http.PostAsJsonAsync(
                $"{BaseUrl}/sdk/v1/optimize", request, RequestJson, ct);
            response.EnsureSuccessStatusCode();
            var result = await response.Content.ReadFromJsonAsync<Result>(ct);
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
        if (!await ReadyAsync(ct))
        {
            return null;
        }

        return api == "openai" ? $"{BaseUrl}/v1" : BaseUrl;
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
