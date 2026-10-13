using System.Net;
using System.Text;
using Gascoigne;
using Xunit;

public sealed class ClientTests : IDisposable
{
    private const string OptimizeReply =
        "{\"text\":\"short\",\"raw_id\":\"abc\",\"raw_tokens\":100,\"out_tokens\":5}";

    private HttpListener? _l;
    private readonly List<string> _posts = new();

    private string Serve(int proto, int optimizeStatus)
    {
        var port = new Random().Next(20000, 40000);
        _l = new HttpListener();
        _l.Prefixes.Add($"http://127.0.0.1:{port}/");
        _l.Start();
        _ = Task.Run(async () =>
        {
            while (_l.IsListening)
            {
                HttpListenerContext c;
                try { c = await _l.GetContextAsync(); } catch { return; }
                string body; var status = 200;
                var path = c.Request.Url!.AbsolutePath;
                if (path.EndsWith("/health")) body = $"{{\"version\":\"t\",\"proto\":{proto}}}";
                else if (path.EndsWith("/optimize"))
                {
                    _posts.Add(await new StreamReader(c.Request.InputStream).ReadToEndAsync());
                    status = optimizeStatus;
                    body = OptimizeReply;
                }
                else body = "original";
                var b = Encoding.UTF8.GetBytes(body);
                c.Response.StatusCode = status;
                await c.Response.OutputStream.WriteAsync(b);
                c.Response.Close();
            }
        });
        return $"127.0.0.1:{port}";
    }

    public void Dispose() => _l?.Stop();

    [Fact]
    public async Task MissingCliWarnsOnceAndPassesThrough()
    {
        var warnings = new List<string>();
        var g = new GascoigneClient(new GascoigneOptions
        {
            Addr = "127.0.0.1:9",
            SearchPath = "",
            Warn = warnings.Add,
        });
        Assert.Equal("hello", await g.OptimizeAsync("hello"));
        Assert.Equal("again", await g.OptimizeAsync("again"));
        Assert.Null(await g.ProxyBaseUrlAsync());
        Assert.Equal("", await g.RawAsync("x"));
        Assert.Single(warnings, w => w.Contains("not found on PATH"));
    }

    [Fact]
    public async Task OptimizesThroughServer()
    {
        var seen = new List<string>();
        var g = new GascoigneClient(new GascoigneOptions
        {
            Agent = "demo",
            Addr = Serve(1, 200),
            OnResult = (_, r) => seen.Add(r.RawId),
        });
        var text = string.Concat(Enumerable.Repeat("long ", 100));
        var res = await g.OptimizeResultAsync(text, new Attrs { Tool = "grep" });
        Assert.Equal(("short", "abc", 5L), (res.Text, res.RawId, res.OutTokens));
        Assert.Contains("\"agent\":\"demo\"", _posts[0]);
        Assert.Contains("\"tool\":\"grep\"", _posts[0]);
        Assert.Equal(new[] { "abc" }, seen);
        Assert.Equal(new Stats(100, 5), g.Stats());
        Assert.EndsWith("/v1", await g.ProxyBaseUrlAsync());
        Assert.Equal("original", await g.RawAsync("abc"));
    }

    [Fact]
    public async Task UnknownProtoBypasses()
    {
        var g = new GascoigneClient(new GascoigneOptions
        {
            Addr = Serve(99, 200),
            SearchPath = "",
            Warn = _ => { },
        });
        Assert.Equal("x", await g.OptimizeAsync("x"));
        Assert.Empty(_posts);
    }

    [Fact]
    public async Task FailuresReturnInputAndOpenBreaker()
    {
        var g = new GascoigneClient(new GascoigneOptions { Addr = Serve(1, 500) });
        for (var i = 0; i < 7; i++) Assert.Equal("text", await g.OptimizeAsync("text"));
        Assert.Equal(5, _posts.Count);
    }

    [Fact]
    public async Task WrapToolOptimizesStrings()
    {
        var g = new GascoigneClient(new GascoigneOptions { Addr = Serve(1, 200) });
        Assert.Equal("short", await g.WrapTool<string>("t", _ => Task.FromResult("big"))("in"));
    }
}
