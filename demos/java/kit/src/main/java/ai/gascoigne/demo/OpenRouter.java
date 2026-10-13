package ai.gascoigne.demo;

/**
 * OpenRouter connection settings, read from the environment or the nearest {@code .env}.
 *
 * @param model model id, for example {@code openai/gpt-4o-mini}
 * @param apiKey the key; a placeholder in a dry run
 * @param baseUrl OpenAI-compatible API root
 */
public record OpenRouter(String model, String apiKey, String baseUrl) {

    /** Loads {@code .env}, then reads the settings; exits with a hint when the key is missing. */
    public static OpenRouter fromEnv() {
        Dotenv.load();
        String apiKey = setting("OPENROUTER_API_KEY", "");
        if (apiKey.isEmpty() && !Demo.dry()) {
            System.err.println("OPENROUTER_API_KEY is not set: copy .env.example to .env");
            System.exit(1);
        }
        String model = setting("OPENROUTER_MODEL", "openai/gpt-4o-mini");
        String key = apiKey.isEmpty() ? "dry-run" : apiKey;
        return new OpenRouter(model, key, "https://openrouter.ai/api/v1");
    }

    /** A real environment variable, else the value {@code .env} put in a system property. */
    private static String setting(String name, String fallback) {
        String value = System.getenv(name);
        return value != null && !value.isEmpty() ? value : System.getProperty(name, fallback);
    }
}
