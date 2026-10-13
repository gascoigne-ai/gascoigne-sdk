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
    /// <summary>Tool name.</summary>
    public string? Tool { get; init; }

    /// <summary>Shell command that produced the text.</summary>
    public string? Cmd { get; init; }

    /// <summary>URL the text was fetched from.</summary>
    public string? Url { get; init; }

    /// <summary>What the agent is looking for; guides lossy selection.</summary>
    public string? Query { get; init; }

    /// <summary>LLM model that will read the text.</summary>
    public string? Model { get; init; }
}

/// <summary>Tokens (estimated) before and after, summed over a client's calls.</summary>
public readonly record struct Stats(long RawTokens, long OutTokens)
{
    /// <summary>Fraction of tokens saved, 0 when nothing was optimized.</summary>
    public double Saved => RawTokens == 0 ? 0 : 1 - (double)OutTokens / RawTokens;
}

/// <summary>Body of <c>POST /sdk/v1/optimize</c>; unset fields are not sent.</summary>
internal sealed record OptimizeRequest(
    string Text,
    string? Agent,
    string? Session,
    string? Tool,
    string? Cmd,
    string? Url,
    string? Query,
    string? Model)
{
    public static OptimizeRequest From(string text, GascoigneOptions options, Attrs? attrs) => new(
        text,
        NullIfEmpty(options.Agent),
        NullIfEmpty(options.Session),
        NullIfEmpty(attrs?.Tool),
        NullIfEmpty(attrs?.Cmd),
        NullIfEmpty(attrs?.Url),
        NullIfEmpty(attrs?.Query),
        NullIfEmpty(attrs?.Model));

    private static string? NullIfEmpty(string? value) => string.IsNullOrEmpty(value) ? null : value;
}

/// <summary>Response of <c>GET /sdk/v1/health</c>.</summary>
internal sealed record Health(
    [property: JsonPropertyName("version")] string? Version,
    [property: JsonPropertyName("proto")] int Proto);
