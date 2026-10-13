using System.Net;
using System.Text;
using Gascoigne;
using Microsoft.Extensions.AI;
using Xunit;

public sealed class FunctionInvocationTests : IDisposable
{
    private const string Reply =
        "{\"text\":\"short [full: gascoigne raw abc]\",\"raw_id\":\"abc\"," +
        "\"raw_tokens\":100,\"out_tokens\":5}";

    private static readonly string Big = string.Concat(Enumerable.Repeat("noisy log line\n", 100));

    private readonly HttpListener _listener = new();
    private int _optimizeCalls;

    public void Dispose() => _listener.Stop();

    private GascoigneClient Gascoigne()
    {
        var port = new Random().Next(40000, 50000);
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

                var isHealth = context.Request.Url!.AbsolutePath.EndsWith("/health");
                if (!isHealth)
                {
                    Interlocked.Increment(ref _optimizeCalls);
                }

                var bytes = Encoding.UTF8.GetBytes(isHealth ? "{\"proto\":1}" : Reply);
                await context.Response.OutputStream.WriteAsync(bytes);
                context.Response.Close();
            }
        });
        return new GascoigneClient(new GascoigneOptions { Addr = $"127.0.0.1:{port}" });
    }

    /// <summary>A model that calls search_logs once, then answers.</summary>
    private sealed class ScriptedModel : IChatClient
    {
        public string? ToolResultSeen { get; private set; }

        public Task<ChatResponse> GetResponseAsync(
            IEnumerable<ChatMessage> messages,
            ChatOptions? options = null,
            CancellationToken cancellationToken = default)
        {
            var result = messages
                .SelectMany(m => m.Contents)
                .OfType<FunctionResultContent>()
                .FirstOrDefault();
            if (result is null)
            {
                var call = new FunctionCallContent("1", "search_logs", null);
                var assistant = new ChatMessage(ChatRole.Assistant, [call]);
                return Task.FromResult(new ChatResponse(assistant));
            }

            ToolResultSeen = result.Result?.ToString();
            var done = new ChatMessage(ChatRole.Assistant, "done");
            return Task.FromResult(new ChatResponse(done));
        }

        public IAsyncEnumerable<ChatResponseUpdate> GetStreamingResponseAsync(
            IEnumerable<ChatMessage> messages,
            ChatOptions? options = null,
            CancellationToken cancellationToken = default) => throw new NotSupportedException();

        public object? GetService(Type serviceType, object? serviceKey = null) =>
            serviceType.IsInstanceOfType(this) ? this : null;

        public void Dispose()
        {
        }
    }

    private async Task<string?> RunAsync(Action<FunctionInvokingChatClient>? configure)
    {
        var model = new ScriptedModel();
        var client = new ChatClientBuilder(model)
            .UseFunctionInvocation(configure: c => configure?.Invoke(c))
            .Build();
        var tool = AIFunctionFactory.Create(() => Big, "search_logs");
        await client.GetResponseAsync("what went wrong?", new ChatOptions { Tools = [tool] });
        return model.ToolResultSeen;
    }

    [Fact]
    public async Task ResultsAreShortenedWhenTheApplicationOptsIn()
    {
        using var gascoigne = Gascoigne();
        var seen = await RunAsync(c => c.UseGascoigne(gascoigne));
        Assert.Equal("short [full: gascoigne raw abc]", seen);
    }

    [Fact]
    public async Task NothingChangesWithoutOptingIn()
    {
        var seen = await RunAsync(configure: null);
        Assert.Equal(Big, seen);
    }

    [Fact]
    public async Task SkippedToolsAndSmallResultsAreLeftAlone()
    {
        using var gascoigne = Gascoigne();
        var options = new GascoigneToolOptions { Skip = ["search_logs"] };
        Assert.Equal(Big, await RunAsync(c => c.UseGascoigne(gascoigne, options)));
        var small = new GascoigneToolOptions { MinChars = 100_000 };
        Assert.Equal(Big, await RunAsync(c => c.UseGascoigne(gascoigne, small)));
        Assert.Equal(0, _optimizeCalls);
    }
}
