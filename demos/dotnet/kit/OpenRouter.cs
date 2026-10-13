namespace Demo;

/// <summary>OpenRouter connection settings, from the environment or the nearest .env.</summary>
/// <param name="Model">Model id, for example openai/gpt-4o-mini.</param>
/// <param name="ApiKey">The key; a placeholder in a dry run.</param>
/// <param name="BaseUrl">OpenAI-compatible API root.</param>
public sealed record OpenRouter(string Model, string ApiKey, string BaseUrl)
{
    /// <summary>Loads .env, then reads the settings; exits with a hint without a key.</summary>
    public static OpenRouter FromEnv()
    {
        Dotenv.Load();
        var apiKey = Environment.GetEnvironmentVariable("OPENROUTER_API_KEY") ?? "";
        if (apiKey.Length == 0 && !Kit.IsDry)
        {
            Console.Error.WriteLine("OPENROUTER_API_KEY is not set: copy .env.example to .env");
            Environment.Exit(1);
        }

        return new OpenRouter(
            Environment.GetEnvironmentVariable("OPENROUTER_MODEL") ?? "openai/gpt-4o-mini",
            apiKey.Length == 0 ? "dry-run" : apiKey,
            Environment.GetEnvironmentVariable("OPENROUTER_BASE_URL")
                ?? "https://openrouter.ai/api/v1");
    }
}
