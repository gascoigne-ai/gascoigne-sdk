package ai.gascoigne;

/**
 * Where a text came from; null fields are left out of the request.
 *
 * @param tool tool name
 * @param cmd shell command that produced the text
 * @param url URL it was fetched from
 * @param query what the agent is looking for; guides lossy selection
 * @param model LLM model that will read the text
 */
public record Attrs(String tool, String cmd, String url, String query, String model) {

    /** No attributes. */
    public static final Attrs NONE = new Attrs(null, null, null, null, null);

    /** Attributes naming only the tool. */
    public static Attrs tool(String name) {
        return new Attrs(name, null, null, null, null);
    }
}
