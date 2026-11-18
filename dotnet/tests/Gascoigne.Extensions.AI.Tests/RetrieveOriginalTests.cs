using System.Net;
using System.Text;
using System.Text.Json;
using Gascoigne;
using Microsoft.Extensions.AI;
using Xunit;

public sealed class RetrieveOriginalTests : IDisposable
{
    private static readonly string Original = File.ReadAllText(
        Path.Combine(AppContext.BaseDirectory, "fixtures", "raw.txt"));

    private readonly HttpListener _listener = new();
    private string? _lastPath;

    public void Dispose() => _listener.Stop();

    private GascoigneClient Server(int rawStatus = 200)
    {
        var port = new Random().Next(50000, 60000);
        _listener.Prefixes.Add($"http://127.0.0.1:{port}/");
        _listener.Start();
        _ = Task.Run(async () =>
        {
            while (_listener.IsListening)
            {
                HttpListenerContext context;
                try
                {
                    context = await _listener.GetContextAsync();
                }
                catch (Exception)
                {
                    return;
                }

                var path = context.Request.Url!.AbsolutePath;
                var isHealth = path.EndsWith("/health");
                if (!isHealth)
                {
                    _lastPath = path;
                }

                context.Response.StatusCode = isHealth ? 200 : rawStatus;
                var body = isHealth ? "{\"proto\":1}" : Original;
                await context.Response.OutputStream.WriteAsync(Encoding.UTF8.GetBytes(body));
                context.Response.Close();
            }
        });
        return new GascoigneClient(new GascoigneOptions { Addr = $"127.0.0.1:{port}" });
    }

    private static async Task<string> Call(AIFunction f, Dictionary<string, object?> args)
    {
        var result = await f.InvokeAsync(new AIFunctionArguments(args));
        return ((JsonElement)result!).GetString()!;
    }

    [Fact]
    public void CreateRejectsNull() =>
        Assert.Throws<ArgumentNullException>(() => RetrieveOriginalFunction.Create(null!));

    [Fact]
    public void DescribesItselfToTheModel()
    {
        using var gascoigne = new GascoigneClient(new GascoigneOptions { Addr = "127.0.0.1:9" });
        var f = RetrieveOriginalFunction.Create(gascoigne);
        Assert.Equal("retrieve_original", f.Name);
        Assert.Contains("gascoigne raw <id>", f.Description);
        var props = f.JsonSchema.GetProperty("properties");
        Assert.Equal(
            ["rawId", "grep", "lines"],
            props.EnumerateObject().Select(p => p.Name).ToArray());
        Assert.Equal(
            ["rawId"],
            f.JsonSchema.GetProperty("required").EnumerateArray()
                .Select(e => e.GetString()!).ToArray());
    }

    // The fixture ends with a newline, so this implementation counts an empty 401st row
    // (Python counts 400 lines). Pinned as is.
    [Fact]
    public async Task ReturnsCappedNumberedLinesOfTheFixtureAndFetchesTheRawRoute()
    {
        using var gascoigne = Server();
        var f = RetrieveOriginalFunction.Create(gascoigne);
        var result = await Call(f, new() { ["rawId"] = "a4e762ac" });
        var rows = Original.ReplaceLineEndings("\n").Split('\n');
        Assert.Equal(401, rows.Length);
        var expected = rows.Take(200).Select((r, i) => $"{i + 1}: {r}")
            .Append("... 201 more lines; narrow with grep or lines");
        Assert.Equal(string.Join('\n', expected), result);
        Assert.EndsWith("/sdk/v1/raw/a4e762ac", _lastPath);
    }

    [Fact]
    public async Task GrepAndLinesNarrowTheResult()
    {
        using var gascoigne = Server();
        var f = RetrieveOriginalFunction.Create(gascoigne);
        var rows = Original.ReplaceLineEndings("\n").Split('\n');
        var grep = await Call(f, new() { ["rawId"] = "x", ["grep"] = "job=2 " });
        Assert.StartsWith($"3: {rows[2]}\n6: {rows[5]}", grep);
        var range = await Call(f, new() { ["rawId"] = "x", ["lines"] = "1-1" });
        Assert.Equal($"1: {rows[0]}", range);
        var both = await Call(f, new() { ["rawId"] = "x", ["grep"] = "job=2 ", ["lines"] = "1-3" });
        Assert.Equal($"3: {rows[2]}", both);
    }

    [Fact]
    public async Task MissingOriginalSaysSo()
    {
        using var gascoigne = Server(rawStatus: 404);
        var f = RetrieveOriginalFunction.Create(gascoigne);
        var result = await Call(f, new() { ["rawId"] = "nope" });
        Assert.Equal("No original stored for nope.", result);
    }

    [Fact]
    public async Task BadSelectionIsReportedNotThrown()
    {
        using var gascoigne = Server();
        var f = RetrieveOriginalFunction.Create(gascoigne);
        var range = await Call(f, new() { ["rawId"] = "x", ["lines"] = "a-b" });
        Assert.Contains("Bad selection:", range);
        var regex = await Call(f, new() { ["rawId"] = "x", ["grep"] = "(" });
        Assert.Contains("Bad selection:", regex);
    }
}
