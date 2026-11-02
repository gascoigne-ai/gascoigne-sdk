// Microsoft.Extensions.AI, native: the engine runs inside this process. No server, no CLI.
using System.ClientModel;
using Demo;
using Gascoigne;
using Microsoft.Extensions.AI;
using OpenAI;

var openRouter = OpenRouter.FromEnv();

// 1. Start gascoigne in native mode. The constructor throws if libgascoigne cannot be found.
using var gascoigne = new GascoigneClient(new GascoigneOptions
{
    Agent = "microsoft-extensions-ai",
    Embedded = new EmbeddedSettings(),
    OnResult = Kit.Observe,
});

var searchLogs = AIFunctionFactory.Create(
    // 2. Optimize what the tool returns.
    () => gascoigne.OptimizeAsync(Kit.NoisyLogs(), new Attrs { Tool = "search_logs" }),
    "search_logs",
    "Return the recent service logs.");

if (Kit.IsDry)
{
    await searchLogs.InvokeAsync();
    Kit.Report(gascoigne, answer: null);
    return;
}

var options = new OpenAIClientOptions { Endpoint = new Uri(openRouter.BaseUrl) };
using IChatClient chat = new ChatClientBuilder(
        new OpenAIClient(new ApiKeyCredential(openRouter.ApiKey), options)
            .GetChatClient(openRouter.Model)
            .AsIChatClient())
    .UseFunctionInvocation()
    .Build();

var response = await chat.GetResponseAsync(Kit.Prompt, new ChatOptions { Tools = [searchLogs] });
Kit.Report(gascoigne, response.Text);
