namespace Gascoigne;

/// <summary>Settings for <see cref="GascoigneClient"/>; the defaults work.</summary>
public sealed class GascoigneOptions
{
    /// <summary>Agent or framework name, for per-agent stats.</summary>
    public string Agent { get; init; } = "";

    /// <summary>Session id, for per-session stats.</summary>
    public string Session { get; init; } = "";

    /// <summary>Per-call timeout.</summary>
    public TimeSpan Timeout { get; init; } = TimeSpan.FromSeconds(5);

    /// <summary>
    /// Server address; default <c>$GASCOIGNE_SERVER_ADDR</c> or 127.0.0.1:7878.
    /// </summary>
    public string? Addr { get; init; }

    /// <summary>
    /// Where to look for the CLI instead of <c>$GASCOIGNE_BIN</c> and <c>$PATH</c>.
    /// </summary>
    public string? SearchPath { get; init; }

    /// <summary>
    /// Sees (original, result) after each optimized call; exceptions in it are ignored.
    /// </summary>
    public Action<string, Result>? OnResult { get; init; }

    /// <summary>Where the one-time warnings go.</summary>
    public Action<string> Warn { get; init; } =
        message => Console.Error.WriteLine($"[gascoigne] {message}");
}
