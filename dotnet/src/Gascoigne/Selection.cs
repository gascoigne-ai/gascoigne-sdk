using System.Globalization;
using System.Text.RegularExpressions;

namespace Gascoigne;

/// <summary>Picks the part of an original that a model asks for.</summary>
internal static class Selection
{
    private const int MaxLines = 200;

    /// <summary>
    /// Numbered lines of <paramref name="text"/>, narrowed by a regex per line and a range such as
    /// "10-20". The result is capped so that asking for the original cannot undo the saving.
    /// </summary>
    public static string Of(string text, string grep, string lines)
    {
        var rows = text.ReplaceLineEndings("\n").Split('\n');
        var (start, end) = ParseRange(lines, rows.Length);
        var pattern = grep.Length == 0
            ? null
            : new Regex(grep, RegexOptions.None, TimeSpan.FromSeconds(1));

        var kept = new List<string>();
        for (var n = Math.Max(start, 1); n <= Math.Min(end, rows.Length); n++)
        {
            if (pattern is null || pattern.IsMatch(rows[n - 1]))
            {
                kept.Add($"{n}: {rows[n - 1]}");
            }
        }

        if (kept.Count > MaxLines)
        {
            var more = kept.Count - MaxLines;
            kept = [.. kept.Take(MaxLines), $"... {more} more lines; narrow with grep or lines"];
        }

        return string.Join('\n', kept);
    }

    private static (int Start, int End) ParseRange(string lines, int count)
    {
        if (lines.Length == 0)
        {
            return (1, count);
        }

        var range = lines.Split('-', 2);
        var start = range[0].Length == 0 ? 1 : Parse(range[0]);
        var end = range.Length < 2 || range[1].Length == 0 ? start : Parse(range[1]);
        return (start, end);
    }

    private static int Parse(string number) =>
        int.Parse(number.Trim(), CultureInfo.InvariantCulture);
}
