using System.Text.Json.Serialization;

namespace Gascoigne;

/// <summary>
/// Configuration for the embedded engine. The library merges it over its built-in defaults and the
/// user's config file; nothing is merged on the .NET side (see spec/native.md).
/// </summary>
public sealed record EmbeddedSettings
{
    /// <summary>YAML laid over the defaults and the user's file.</summary>
    [JsonPropertyName("config")]
    public string? Config { get; init; }

    /// <summary>"dotted.path=value" assignments applied last.</summary>
    [JsonPropertyName("set")]
    public IReadOnlyList<string>? Set { get; init; }

    /// <summary>Keeps just these optimizers in every chain.</summary>
    [JsonPropertyName("only")]
    public IReadOnlyList<string>? Only { get; init; }

    /// <summary>Drops these optimizers from every chain.</summary>
    [JsonPropertyName("disable")]
    public IReadOnlyList<string>? Disable { get; init; }

    /// <summary>Skips the user's config file.</summary>
    [JsonPropertyName("ignore_user_file")]
    public bool IgnoreUserFile { get; init; }

    /// <summary>Per-call bound inside the library in milliseconds; 0 for its default.</summary>
    [JsonPropertyName("timeout_ms")]
    public int TimeoutMs { get; init; }

    /// <summary>
    /// "file" (default: the configured sqlite file) or "memory" (private to this process).
    /// </summary>
    [JsonPropertyName("ledger")]
    public string? Ledger { get; init; }

    /// <summary>Prices behind <see cref="GascoigneClient.CostsAsync"/>.</summary>
    [JsonPropertyName("pricing")]
    public Pricing? Pricing { get; init; }
}

/// <summary>
/// Where dollar figures come from for the embedded engine. Prices are held per process, not per
/// client.
/// </summary>
public sealed record Pricing
{
    /// <summary>"api" (default) or "subscription": a flat plan has no dollars.</summary>
    [JsonPropertyName("billing")]
    public string? Billing { get; init; }

    /// <summary>Static prices by model id.</summary>
    [JsonPropertyName("prices")]
    public IReadOnlyDictionary<string, Price>? Prices { get; init; }

    /// <summary>A price sheet (JSON) read once when the engine opens.</summary>
    [JsonPropertyName("file")]
    public string? File { get; init; }
}

/// <summary>One model's price, dollars per million tokens.</summary>
public sealed record Price
{
    /// <summary>Required.</summary>
    [JsonPropertyName("in")]
    public double In { get; init; }

    /// <summary>Required.</summary>
    [JsonPropertyName("out")]
    public double Out { get; init; }

    /// <summary>Defaults to <see cref="In"/>.</summary>
    [JsonPropertyName("cache_read")]
    public double? CacheRead { get; init; }

    /// <summary>Defaults to <see cref="In"/>.</summary>
    [JsonPropertyName("cache_write")]
    public double? CacheWrite { get; init; }

    /// <summary>o200k (default), claude, claude-legacy or gemini.</summary>
    [JsonPropertyName("tokenizer")]
    public string? Tokenizer { get; init; }
}
