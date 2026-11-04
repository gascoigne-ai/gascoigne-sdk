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

/// <summary>The recorded runs of one group, summed.</summary>
public sealed record Total(
    [property: JsonPropertyName("group")] string Group = "",
    [property: JsonPropertyName("runs")] long Runs = 0,
    [property: JsonPropertyName("optimized")] long Optimized = 0,
    [property: JsonPropertyName("failed")] long Failed = 0,
    [property: JsonPropertyName("raw_tokens")] long RawTokens = 0,
    [property: JsonPropertyName("out_tokens")] long OutTokens = 0,
    [property: JsonPropertyName("saved")] long Saved = 0,
    [property: JsonPropertyName("first")] string First = "",
    [property: JsonPropertyName("last")] string Last = "");

/// <summary>One recorded optimization.</summary>
public sealed record Run
{
    /// <summary>Run id, for paging with <see cref="RunsQuery.Before"/>.</summary>
    [JsonPropertyName("id")] public long Id { get; init; }

    /// <summary>RFC 3339.</summary>
    [JsonPropertyName("time")] public string Time { get; init; } = "";

    /// <inheritdoc/>
    [JsonPropertyName("session")] public string Session { get; init; } = "";

    /// <inheritdoc/>
    [JsonPropertyName("agent")] public string Agent { get; init; } = "";

    /// <inheritdoc/>
    [JsonPropertyName("model")] public string Model { get; init; } = "";

    /// <inheritdoc/>
    [JsonPropertyName("command")] public string Command { get; init; } = "";

    /// <inheritdoc/>
    [JsonPropertyName("route")] public string Route { get; init; } = "";

    /// <inheritdoc/>
    [JsonPropertyName("optimizers")] public IReadOnlyList<string> Optimizers { get; init; } = [];

    /// <inheritdoc/>
    [JsonPropertyName("raw_tokens")] public long RawTokens { get; init; }

    /// <inheritdoc/>
    [JsonPropertyName("out_tokens")] public long OutTokens { get; init; }

    /// <inheritdoc/>
    [JsonPropertyName("duration_ns")] public long DurationNs { get; init; }

    /// <summary>Id of the stored original, see <see cref="GascoigneClient.RawAsync"/>.</summary>
    [JsonPropertyName("raw_id")] public string RawId { get; init; } = "";

    /// <summary>optimized, unchanged, bypassed, rerequested or error.</summary>
    [JsonPropertyName("outcome")] public string Outcome { get; init; } = "";

    /// <inheritdoc/>
    [JsonPropertyName("reason")] public string Reason { get; init; } = "";
}

/// <summary>The tokens saved, priced for one model.</summary>
public sealed record ModelCost
{
    /// <inheritdoc/>
    [JsonPropertyName("model")] public string Model { get; init; } = "";

    /// <summary>Where the price comes from: built-in, static, json, api or script.</summary>
    [JsonPropertyName("source")] public string Source { get; init; } = "";

    /// <inheritdoc/>
    [JsonPropertyName("assumed")] public bool Assumed { get; init; }

    /// <inheritdoc/>
    [JsonPropertyName("tokenizer")] public string Tokenizer { get; init; } = "";

    /// <summary>Saved, in gascoigne's estimate units.</summary>
    [JsonPropertyName("tokens")] public long Tokens { get; init; }

    /// <summary>Saved, in the model's own tokens.</summary>
    [JsonPropertyName("model_tokens")] public long ModelTokens { get; init; }

    /// <inheritdoc/>
    [JsonPropertyName("first_read_usd")] public double FirstReadUsd { get; init; }

    /// <inheritdoc/>
    [JsonPropertyName("in_context_usd")] public double InContextUsd { get; init; }
}

/// <summary>
/// What the tokens saved are worth: an estimate from list prices or the prices configured for
/// gascoigne, not what anyone is billed. With <see cref="Billing"/> "subscription" there are no
/// dollars.
/// </summary>
public sealed record Costs
{
    /// <inheritdoc/>
    [JsonPropertyName("billing")] public string Billing { get; init; } = "";

    /// <inheritdoc/>
    [JsonPropertyName("first_read_usd")] public double FirstReadUsd { get; init; }

    /// <inheritdoc/>
    [JsonPropertyName("in_context_usd")] public double InContextUsd { get; init; }

    /// <inheritdoc/>
    [JsonPropertyName("rereads")] public double Rereads { get; init; }

    /// <inheritdoc/>
    [JsonPropertyName("savings")] public IReadOnlyList<ModelCost> Savings { get; init; } = [];

    /// <inheritdoc/>
    [JsonPropertyName("unpriced")] public IReadOnlyList<string> Unpriced { get; init; } = [];
}

/// <summary>
/// Filters for <see cref="GascoigneClient.TotalsAsync"/> and
/// <see cref="GascoigneClient.CostsAsync"/>; unset ones match everything.
/// </summary>
public sealed record TotalsQuery
{
    /// <summary>
    /// route (default), session, family, optimizer, command, outcome, agent, model, day, week or
    /// month; totals only.
    /// </summary>
    public string? By { get; init; }

    /// <inheritdoc/>
    public string? Session { get; init; }

    /// <inheritdoc/>
    public string? Agent { get; init; }

    /// <inheritdoc/>
    public string? Model { get; init; }

    /// <summary>Only runs from this time on.</summary>
    public DateTimeOffset? Since { get; init; }
}

/// <summary>Filters for <see cref="GascoigneClient.RunsAsync"/>, newest first.</summary>
public sealed record RunsQuery
{
    /// <inheritdoc/>
    public string? Session { get; init; }

    /// <inheritdoc/>
    public string? Agent { get; init; }

    /// <inheritdoc/>
    public string? Model { get; init; }

    /// <inheritdoc/>
    public DateTimeOffset? Since { get; init; }

    /// <summary>A run id: only older runs come back, to page; 0 for none.</summary>
    public long Before { get; init; }

    /// <summary>At most this many; 0 means 50, the most is 1000.</summary>
    public int Limit { get; init; }
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
