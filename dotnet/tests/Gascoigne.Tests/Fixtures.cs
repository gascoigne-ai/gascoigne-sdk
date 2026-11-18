using System.Text.Json;
using Gascoigne;

/// <summary>Real server responses from spec/fixtures, copied next to the test binary.</summary>
internal static class Fixtures
{
    public static string Read(string name) =>
        File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "fixtures", name));

    public static Result Optimized { get; } = Json<Result>("optimize_optimized.json");

    public static string Raw => Read("raw.txt");

    public static string Health => Read("health.json");

    public static string Stats => Read("stats.json");

    public static string Recent => Read("recent.json");

    public static string Skipped => Read("optimize_skipped.json");

    public static string OptimizedJson => Read("optimize_optimized.json");

    public static T Json<T>(string name) => JsonSerializer.Deserialize<T>(Read(name))!;
}
