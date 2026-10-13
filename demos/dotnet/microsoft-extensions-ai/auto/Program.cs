// Microsoft.Extensions.AI + OpenRouter with gascoigne enabled for every function call.
using System.ClientModel;
using Demo;
using Gascoigne;
using Microsoft.Extensions.AI;
using OpenAI;

var openRouter = OpenRouter.FromEnv();

// 1. Start gascoigne.
using var gascoigne = new GascoigneClient(new GascoigneOptions
{
    Agent = "microsoft-extensions-ai",
    OnResult = Kit.Observe,
});

// The tools know nothing about gascoigne. The retrieve tool lets the model fetch a folded original.
var searchLogs = AIFunctionFactory.Create(
    Kit.NoisyLogs, "search_logs", "Return the recent service logs.");
var retrieve = RetrieveOriginalFunction.Create(gascoigne);

if (Kit.IsDry)
{
    Console.WriteLine("Dry run: function calls are decorated inside the LLM loop.");
    return;
}

var options = new OpenAIClientOptions { Endpoint = new Uri(openRouter.BaseUrl) };
using IChatClient chat = new ChatClientBuilder(
        new OpenAIClient(new ApiKeyCredential(openRouter.ApiKey), options)
            .GetChatClient(openRouter.Model)
            .AsIChatClient())
    // 2. Opt in, explicitly: without this call nothing is decorated.
    .UseFunctionInvocation(configure: c => c.UseGascoigne(
        gascoigne, new GascoigneToolOptions { Skip = ["retrieve_original"] }))
    .Build();

var response = await chat.GetResponseAsync(
    Kit.Prompt, new ChatOptions { Tools = [searchLogs, retrieve] });
Kit.Report(gascoigne, response.Text);
