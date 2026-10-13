using System.Globalization;
using Gascoigne;

namespace Demo;

/// <summary>The noisy tool and the before/after report shared by the .NET demos.</summary>
public static class Kit
{
    /// <summary>What every demo asks.</summary>
    public const string Prompt = "Call the search_logs tool once, then tell me in one sentence "
        + "what went wrong and for how long.";

    private const string Info =
        "2026-10-13T12:{0:00}:{1:00}Z INFO worker-{2} handled request id={3} status=200 took={4}ms";

    private const string Error =
        "2026-10-13T12:04:10Z ERROR db connection timeout after 30s (pool exhausted)";

    private static string _before = "";
    private static Result? _last;

    /// <summary>True for a run without LLM calls.</summary>
    public static bool IsDry => Environment.GetEnvironmentVariable("GASCOIGNE_DEMO_DRY") == "1";

    /// <summary>The noisy tool: 400 near-identical lines and one error.</summary>
    public static string NoisyLogs()
    {
        // Request ids differ per call, as in real logs; the proxy caches identical results.
        var firstId = Random.Shared.Next(900_000);
        var lines = Enumerable.Range(0, 400)
            .Select(i => Line(i, firstId + i))
            .ToList();
        lines.Insert(250, Error);
        return string.Join('\n', lines);
    }

    /// <summary>An <c>OnResult</c> hook that remembers the last call for the report.</summary>
    public static void Observe(string original, Result result)
    {
        _before = original;
        _last = result;
    }

    /// <summary>Prints the answer (if any) and what gascoigne saved.</summary>
    public static void Report(GascoigneClient gascoigne, string? answer)
    {
        if (!string.IsNullOrWhiteSpace(answer))
        {
            Console.WriteLine($"Model answer:\n{Indent(answer.Trim())}\n");
        }

        if (_last is null)
        {
            Console.WriteLine("No optimization happened. Is the gascoigne CLI on PATH?");
            Console.WriteLine(
                "Install: mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne");
            return;
        }

        Console.WriteLine($"Tool result: {_last.RawTokens:N0} tokens\n{Preview(_before)}\n");
        Console.WriteLine($"Model reads: {_last.OutTokens:N0} tokens\n{Preview(_last.Text)}\n");
        var stats = gascoigne.Stats();
        Console.WriteLine(
            $"Saved {stats.Saved:P0}: {stats.RawTokens:N0} -> {stats.OutTokens:N0} tokens.");
        Console.WriteLine($"Original: gascoigne raw {_last.RawId}");
    }

    private static string Preview(string text)
    {
        var rows = text.Split('\n').Select(r => r[..Math.Min(r.Length, 72)]).ToList();
        var shown = rows.Take(8).ToList();
        if (rows.Count > 8)
        {
            shown.Add($"... {rows.Count - 8} more lines");
        }

        return Indent(string.Join('\n', shown));
    }

    private static string Line(int i, int id) => string.Format(
        CultureInfo.InvariantCulture, Info, i / 60, i % 60, i % 7, id, i % 90);

    private static string Indent(string text) =>
        "  " + text.Replace("\n", "\n  ", StringComparison.Ordinal);
}
