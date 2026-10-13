using System.Diagnostics;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Gascoigne;

/// <summary>One optimize call: <see cref="Text"/> is what the model should read.</summary>
public sealed record Result(
    [property: JsonPropertyName("text")] string Text,
    [property: JsonPropertyName("raw_id")] string RawId = "",
    [property: JsonPropertyName("raw_tokens")] long RawTokens = 0,
    [property: JsonPropertyName("out_tokens")] long OutTokens = 0,
    [property: JsonPropertyName("skipped")] string Skipped = "");

/// <summary>Where the text came from; null fields are left out.</summary>
public sealed record Attrs
{
    public string? Tool { get; init; }
    public string? Cmd { get; init; }
    public string? Url { get; init; }
    public string? Query { get; init; }
    public string? Model { get; init; }
}

public sealed class GascoigneOptions
{
    public string Agent { get; init; } = "";
    public string Session { get; init; } = "";
    public TimeSpan Timeout { get; init; } = TimeSpan.FromSeconds(5);
    /// <summary>Server address; default <c>$GASCOIGNE_SERVER_ADDR</c> or 127.0.0.1:7878.</summary>
    public string? Addr { get; init; }
    /// <summary>Where to look for the CLI instead of <c>$GASCOIGNE_BIN</c> and <c>$PATH</c>.</summary>
    public string? SearchPath { get; init; }
    /// <summary>Sees (original, result) after each optimized call; exceptions in it are ignored.</summary>
    public Action<string, Result>? OnResult { get; init; }
    public Action<string> Warn { get; init; } = m => Console.Error.WriteLine("[gascoigne] " + m);
}

/// <summary>
/// Finds the CLI, makes sure its server runs, and optimizes text through it. Every call is safe:
/// when the CLI is missing or the server misbehaves, inputs come back unchanged.
/// </summary>
public sealed class GascoigneClient
{
    private const int Proto = 1;
    private const string DefaultAddr = "127.0.0.1:7878";
    private const string InstallHint = "mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne";
    private const int BreakerFailures = 5;
    private static readonly TimeSpan BreakerPause = TimeSpan.FromSeconds(60);

    private readonly GascoigneOptions _o;
    private readonly HttpClient _http;
    private readonly SemaphoreSlim _probe = new(1, 1);
    private readonly object _lock = new();
    private bool? _ready;
    private int _failures;
    private DateTime _pausedUntil = DateTime.MinValue;
    private bool _warned;
    private long _rawTokens, _outTokens;

    public GascoigneClient(GascoigneOptions? options = null)
    {
        _o = options ?? new GascoigneOptions();
        _http = new HttpClient { Timeout = _o.Timeout };
    }

    private string BaseUrl
    {
        get
        {
            var a = _o.Addr ?? Environment.GetEnvironmentVariable("GASCOIGNE_SERVER_ADDR");
            return "http://" + (string.IsNullOrEmpty(a) ? DefaultAddr : a);
        }
    }

    private static bool EnvIs(string name, string value) => Environment.GetEnvironmentVariable(name) == value;

    private void Warn(string msg)
    {
        lock (_lock)
        {
            if (_warned) return;
            _warned = true;
        }
        _o.Warn(msg);
    }

    private async Task<bool> HealthyAsync(CancellationToken ct)
    {
        try
        {
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            cts.CancelAfter(TimeSpan.FromMilliseconds(500));
            using var resp = await _http.GetAsync($"{BaseUrl}/sdk/v1/health", cts.Token);
            if (!resp.IsSuccessStatusCode) return false;
            using var doc = await JsonDocument.ParseAsync(await resp.Content.ReadAsStreamAsync(cts.Token), cancellationToken: cts.Token);
            var proto = doc.RootElement.TryGetProperty("proto", out var p) ? p.GetInt32() : -1;
            if (proto == Proto) return true;
            Warn($"server speaks proto {proto}, SDK {Proto}; running without optimization");
            return false;
        }
        catch (Exception e) when (e is HttpRequestException or TaskCanceledException or JsonException or InvalidOperationException)
        {
            return false;
        }
    }

    private string? FindCli()
    {
        var bin = Environment.GetEnvironmentVariable("GASCOIGNE_BIN");
        if (_o.SearchPath is null && !string.IsNullOrEmpty(bin)) return bin;
        var path = _o.SearchPath ?? Environment.GetEnvironmentVariable("PATH") ?? "";
        var names = OperatingSystem.IsWindows() ? new[] { "gascoigne.exe" } : new[] { "gascoigne" };
        return path.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries)
            .SelectMany(d => names.Select(n => Path.Combine(d, n))).FirstOrDefault(File.Exists);
    }

    private async Task<bool> StartServerAsync(CancellationToken ct)
    {
        var exe = FindCli();
        if (exe is null)
        {
            Warn("gascoigne-cli not found on PATH; running without optimization. Install: " + InstallHint);
            return false;
        }
        try
        {
            using var p = Process.Start(new ProcessStartInfo(exe, "server start")
            { RedirectStandardOutput = true, RedirectStandardError = true, UseShellExecute = false })!;
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            cts.CancelAfter(TimeSpan.FromSeconds(10));
            await p.WaitForExitAsync(cts.Token);
        }
        catch (Exception e) when (e is System.ComponentModel.Win32Exception or OperationCanceledException or InvalidOperationException)
        {
            Warn($"could not start gascoigne server ({e.Message}); running without optimization");
            return false;
        }
        for (var end = DateTime.UtcNow.AddSeconds(3); DateTime.UtcNow < end; await Task.Delay(100, ct))
            if (await HealthyAsync(ct)) return true;
        Warn("gascoigne server did not come up; running without optimization");
        return false;
    }

    /// <summary>True when optimize calls will be tried. Probes once, then remembers.</summary>
    public async Task<bool> ReadyAsync(CancellationToken ct = default)
    {
        if (EnvIs("GASCOIGNE_SDK", "off") || EnvIs("GASCOIGNE_SERVER", "off")) return false;
        if (_ready is null)
        {
            await _probe.WaitAsync(ct);
            try { _ready ??= await HealthyAsync(ct) || await StartServerAsync(ct); }
            finally { _probe.Release(); }
        }
        return _ready == true && DateTime.UtcNow >= _pausedUntil;
    }

    private void Failed()
    {
        lock (_lock)
        {
            if (++_failures < BreakerFailures) return;
            _failures = 0;
            _pausedUntil = DateTime.UtcNow + BreakerPause;
        }
    }

    /// <summary>Optimizes text; on any problem the result carries the input unchanged.</summary>
    public async Task<Result> OptimizeResultAsync(string text, Attrs? attrs = null, CancellationToken ct = default)
    {
        var same = new Result(text);
        if (string.IsNullOrEmpty(text) || !await ReadyAsync(ct)) return same;
        var body = new Dictionary<string, string> { ["text"] = text };
        void Put(string k, string? v) { if (!string.IsNullOrEmpty(v)) body[k] = v; }
        Put("agent", _o.Agent); Put("session", _o.Session);
        Put("tool", attrs?.Tool); Put("cmd", attrs?.Cmd); Put("url", attrs?.Url);
        Put("query", attrs?.Query); Put("model", attrs?.Model);
        try
        {
            using var resp = await _http.PostAsJsonAsync($"{BaseUrl}/sdk/v1/optimize", body, ct);
            resp.EnsureSuccessStatusCode();
            var res = await resp.Content.ReadFromJsonAsync<Result>(ct);
            if (res is null || res.Text is null) { Failed(); return same; }
            lock (_lock)
            {
                _failures = 0;
                _rawTokens += res.RawTokens;
                _outTokens += res.OutTokens > 0 ? res.OutTokens : res.RawTokens;
            }
            try { _o.OnResult?.Invoke(text, res); } catch { /* an observer must never break the app */ }
            return res;
        }
        catch (Exception e) when (e is HttpRequestException or TaskCanceledException or JsonException or NotSupportedException)
        {
            Failed();
            return same;
        }
    }

    public async Task<string> OptimizeAsync(string text, Attrs? attrs = null, CancellationToken ct = default)
        => (await OptimizeResultAsync(text, attrs, ct)).Text;

    /// <summary>The original behind an optimized result; empty when unavailable.</summary>
    public async Task<string> RawAsync(string rawId, CancellationToken ct = default)
    {
        if (!await ReadyAsync(ct)) return "";
        try { return await _http.GetStringAsync($"{BaseUrl}/sdk/v1/raw/{Uri.EscapeDataString(rawId)}", ct); }
        catch (Exception e) when (e is HttpRequestException or TaskCanceledException) { Failed(); return ""; }
    }

    /// <summary>Base URL that routes an LLM client through the gascoigne proxy, null in bypass.</summary>
    public async Task<string?> ProxyBaseUrlAsync(string api = "openai", CancellationToken ct = default)
        => await ReadyAsync(ct) ? (api == "openai" ? BaseUrl + "/v1" : BaseUrl) : null;

    /// <summary>Tokens (estimated) before and after, summed over this client's calls.</summary>
    public (long Raw, long Out) Stats() { lock (_lock) return (_rawTokens, _outTokens); }

    /// <summary>Wraps a string-returning tool body, e.g. a Semantic Kernel function or an AIFunction.</summary>
    public Func<TArg, Task<string>> WrapTool<TArg>(string name, Func<TArg, Task<string>> fn)
        => async a => await OptimizeAsync(await fn(a), new Attrs { Tool = name });
}
