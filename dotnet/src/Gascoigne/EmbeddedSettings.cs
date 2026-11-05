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
}
