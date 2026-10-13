using System.Text.Json;
using Microsoft.Extensions.AI;

namespace Gascoigne;

/// <summary>Settings for <see cref="GascoigneFunctionInvocation.UseGascoigne"/>.</summary>
public sealed class GascoigneToolOptions
{
    /// <summary>Names of functions whose results are never touched.</summary>
    public IReadOnlyCollection<string> Skip { get; init; } = [];

    /// <summary>Results shorter than this are not sent to gascoigne at all.</summary>
    public int MinChars { get; init; } = 800;
}

/// <summary>Opt-in gascoigne for every function a chat client invokes.</summary>
public static class GascoigneFunctionInvocation
{
    // Text gascoigne appends to what it shortened; such text is never optimized twice.
    private const string Hint = "full: gascoigne raw";

    /// <summary>
    /// Shortens the text each function returns before the model reads it. Every tool goes through
    /// <see cref="FunctionInvokingChatClient.FunctionInvoker"/>, so plain functions and MCP tools
    /// are covered alike. Nothing is decorated unless an application calls this method.
    /// </summary>
    /// <example>
    /// <code>
    /// new ChatClientBuilder(inner)
    ///     .UseFunctionInvocation(configure: c => c.UseGascoigne(gascoigne))
    ///     .Build();
    /// </code>
    /// </example>
    public static FunctionInvokingChatClient UseGascoigne(
        this FunctionInvokingChatClient client,
        GascoigneClient gascoigne,
        GascoigneToolOptions? options = null)
    {
        ArgumentNullException.ThrowIfNull(client);
        ArgumentNullException.ThrowIfNull(gascoigne);
        options ??= new GascoigneToolOptions();
        var invoke = client.FunctionInvoker ?? InvokeFunction;
        client.FunctionInvoker = async (context, ct) =>
        {
            var result = await invoke(context, ct);
            return await ShortenAsync(gascoigne, options, context.Function.Name, result, ct);
        };
        return client;
    }

    private static ValueTask<object?> InvokeFunction(
        FunctionInvocationContext context, CancellationToken ct) =>
        context.Function.InvokeAsync(context.Arguments, ct);

    private static async ValueTask<object?> ShortenAsync(
        GascoigneClient gascoigne,
        GascoigneToolOptions options,
        string tool,
        object? result,
        CancellationToken ct)
    {
        var text = result switch
        {
            string s => s,
            JsonElement { ValueKind: JsonValueKind.String } e => e.GetString(),
            _ => null,
        };
        if (text is null || options.Skip.Contains(tool) || text.Length < options.MinChars
            || text.Contains(Hint, StringComparison.Ordinal))
        {
            return result;
        }

        var shortened = await gascoigne.OptimizeAsync(text, new Attrs { Tool = tool }, ct);
        return result is string ? shortened : JsonSerializer.SerializeToElement(shortened);
    }
}
