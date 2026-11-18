using Gascoigne;
using Xunit;

public sealed class SelectionTests
{
    public static TheoryData<string, string> Texts => new()
    {
        { "a\nb", "1: a\n2: b" },
        { "a\nb\n", "1: a\n2: b" },
        { "a\r\nb\r\n", "1: a\n2: b" },
        // A real blank last line is kept: only the one terminator is dropped.
        { "a\n\n", "1: a\n2: " },
        { "\n", "1: " },
        { "", "" },
    };

    public static TheoryData<string, string, string, string> Narrowed => new()
    {
        { "a\nb\n", "", "3", "" },
        { "a\nb\n", "", "2-9", "2: b" },
        { "a\n", "^$", "", "" },
    };

    [Theory]
    [MemberData(nameof(Texts))]
    public void CountsLinesLikePython(string text, string expected) =>
        Assert.Equal(expected, Selection.Of(text, "", ""));

    [Theory]
    [MemberData(nameof(Narrowed))]
    public void TrailingNewlineAddsNoRowToSelections(
        string text, string grep, string lines, string expected) =>
        Assert.Equal(expected, Selection.Of(text, grep, lines));

    [Fact]
    public void ExactlyTheCapWithTrailingNewlineHasNoNote()
    {
        var text = string.Concat(Enumerable.Range(1, 200).Select(number => $"l{number}\n"));
        var result = Selection.Of(text, "", "");
        Assert.DoesNotContain("more lines", result);
        Assert.EndsWith("200: l200", result);
    }

    [Fact]
    public void OneOverTheCapWithTrailingNewlineCountsOneMore()
    {
        var text = string.Concat(Enumerable.Range(1, 201).Select(number => $"l{number}\n"));
        Assert.EndsWith(
            "\n... 1 more lines; narrow with grep or lines", Selection.Of(text, "", ""));
    }
}
