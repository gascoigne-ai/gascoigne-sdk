using System.Net;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Gascoigne;
using Xunit;

public sealed class LedgerTests : IDisposable
{
    private const string Totals = "[{\"group\":\"sdk\",\"runs\":2,\"optimized\":2,\"failed\":0,"
        + "\"raw_tokens\":100,\"out_tokens\":40,\"saved\":60}]";
    private const string Runs = "[{\"id\":7,\"time\":\"2026-11-01T10:00:00Z\",\"session\":\"s1\","
        + "\"raw_tokens\":100,\"out_tokens\":10,\"raw_id\":\"abc\",\"outcome\":\"optimized\","
        + "\"optimizers\":[\"log\"]}]";
    private const string CostsBody = "{\"billing\":\"api\",\"first_read_usd\":0.5,"
        + "\"in_context_usd\":1.5,\"rereads\":110,\"savings\":[{\"model\":\"m\","
        + "\"source\":\"static\","
        + "\"tokenizer\":\"o200k\",\"tokens\":10,\"model_tokens\":10,\"first_read_usd\":0.5,"
        + "\"in_context_usd\":1.5}]}";
    private static readonly string Lib = Path.GetFullPath(
        Path.Combine(AppContext.BaseDirectory, "../../../../../../native/dist/libgascoigne.so"));

    private HttpListener? _l;
    private readonly List<string> _urls = new();

    private string Serve(int status)
    {
        var port = new Random().Next(40001, 60000);
        _l = new HttpListener();
        _l.Prefixes.Add($"http://127.0.0.1:{port}/");
        _l.Start();
        _ = Task.Run(async () =>
        {
            while (_l.IsListening)
            {
                HttpListenerContext c;
                try { c = await _l.GetContextAsync(); } catch { return; }
                var path = c.Request.Url!.AbsolutePath;
                string body;
                var code = 200;
                if (path.EndsWith("/health")) body = "{\"version\":\"t\",\"proto\":1}";
                else
                {
                    _urls.Add(c.Request.Url!.PathAndQuery);
                    code = status;
                    body = status != 200 ? "boom"
                        : path.EndsWith("/stats") ? Totals
                        : path.EndsWith("/recent") ? Runs : CostsBody;
                }
                var b = Encoding.UTF8.GetBytes(body);
                c.Response.StatusCode = code;
                await c.Response.OutputStream.WriteAsync(b);
                c.Response.Close();
            }
        });
        return $"127.0.0.1:{port}";
    }

    public void Dispose() => _l?.Stop();

    private static void SameQuery(string expected, string actual)
    {
        Assert.Equal(expected.Split('?')[0], actual.Split('?')[0]);
        Assert.Equal(
            expected.Split('?')[1].Split('&').Order(), actual.Split('?')[1].Split('&').Order());
    }

    [Fact]
    public async Task ReadsThroughTheServer()
    {
        using var g = new GascoigneClient(new GascoigneOptions { Addr = Serve(200) });
        var totals = await g.TotalsAsync(new TotalsQuery
        {
            By = "agent",
            Session = "s 1",
            Since = DateTimeOffset.Parse("2026-11-01T00:00:00Z"),
        });
        var total = Assert.Single(totals);
        Assert.Equal(new Total("sdk", 2, 2, 0, 100, 40, 60), total);
        SameQuery("/sdk/v1/stats?by=agent&session=s+1&since=2026-11-01T00%3A00%3A00Z", _urls[0]);
        var runs = await g.RunsAsync(new RunsQuery { Session = "s1", Limit = 5, Before = 9 });
        Assert.Equal(7, runs[0].Id);
        Assert.Equal("abc", runs[0].RawId);
        Assert.Equal(new[] { "log" }, runs[0].Optimizers);
        SameQuery("/sdk/v1/recent?before=9&limit=5&session=s1", _urls[1]);
        var costs = await g.CostsAsync();
        Assert.Equal("api", costs.Billing);
        Assert.Equal(1.5, costs.InContextUsd);
        Assert.Equal("static", costs.Savings[0].Source);
    }

    [Fact]
    public async Task FailuresAreEmptyNotExceptionsAndKeepTheBreakerClosed()
    {
        using var g = new GascoigneClient(new GascoigneOptions { Addr = Serve(500) });
        for (var i = 0; i < 10; i++)
        {
            Assert.Empty(await g.TotalsAsync());
        }

        Assert.Empty(await g.RunsAsync());
        Assert.Equal("", (await g.CostsAsync()).Billing);
        Assert.True(await g.ReadyAsync());
    }

    [Fact]
    public async Task BypassIsEmpty()
    {
        using var g = new GascoigneClient(new GascoigneOptions
        {
            Addr = "127.0.0.1:9",
            SearchPath = "",
            Warn = _ => { },
        });
        Assert.Empty(await g.TotalsAsync());
        Assert.Empty((await g.CostsAsync()).Savings);
    }

    [Fact]
    public void SettingsCarryLedgerAndPricing()
    {
        var settings = new EmbeddedSettings
        {
            Ledger = "memory",
            Pricing = new Pricing
            {
                Billing = "subscription",
                Prices = new Dictionary<string, Price> { ["m"] = new() { In = 1, Out = 2 } },
            },
        };
        // The engine drops defaults and nulls; compare what is set.
        var json = JsonDocument.Parse(JsonSerializer.Serialize(settings, new JsonSerializerOptions
        {
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingDefault,
        })).RootElement;
        Assert.Equal("memory", json.GetProperty("ledger").GetString());
        var pricing = json.GetProperty("pricing");
        Assert.Equal("subscription", pricing.GetProperty("billing").GetString());
        var price = pricing.GetProperty("prices").GetProperty("m");
        Assert.Equal(1, price.GetProperty("in").GetDouble());
        Assert.False(pricing.TryGetProperty("file", out _));
        Assert.False(json.TryGetProperty("config", out _));
    }

    [Fact]
    public async Task EmbeddedMemoryLedger()
    {
        if (!File.Exists(Lib))
        {
            return;
        }

        using var client = new GascoigneClient(new GascoigneOptions
        {
            Library = Lib,
            Agent = "sdk",
            Session = "s1",
            Embedded = new EmbeddedSettings
            {
                IgnoreUserFile = true,
                Ledger = "memory",
                Pricing = new Pricing
                {
                    Prices = new Dictionary<string, Price>
                    {
                        ["acme-large"] = new() { In = 3, Out = 15, Tokenizer = "claude" },
                    },
                },
            },
        });
        var raw = string.Concat(Enumerable.Repeat(
            "INFO request served path=/api/items status=200 ms=12\n", 400));
        await client.OptimizeResultAsync(raw, new Attrs { Tool = "bash", Model = "acme-large" });
        var totals = await client.TotalsAsync(new TotalsQuery { By = "agent" });
        Assert.Equal("sdk", totals[0].Group);
        Assert.Equal(1, totals[0].Runs);
        Assert.True(totals[0].Saved > 0);
        var runs = await client.RunsAsync(new RunsQuery { Session = "s1" });
        Assert.Single(runs);
        Assert.NotEmpty(runs[0].RawId);
        var costs = await client.CostsAsync();
        Assert.True(costs.InContextUsd > 0);
        Assert.Equal("static", costs.Savings[0].Source);
        Assert.Empty(await client.TotalsAsync(new TotalsQuery { By = "nonsense" }));
    }
}
