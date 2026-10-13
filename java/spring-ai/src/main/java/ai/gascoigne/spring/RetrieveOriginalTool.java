package ai.gascoigne.spring;

import ai.gascoigne.Gascoigne;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;

/**
 * Gives the model a way to follow a "gascoigne raw" hint: add an instance to the tools of a
 * {@code ChatClient}, and register its name in {@code @EnableGascoigne(skip = ...)}.
 */
public final class RetrieveOriginalTool {
    private final Gascoigne gascoigne;

    /** Creates the tool for the given client. */
    public RetrieveOriginalTool(Gascoigne gascoigne) {
        this.gascoigne = gascoigne;
    }

    /** Returns lines of the original output behind a "gascoigne raw" hint. */
    @Tool(
            name = "retrieve_original",
            description = "Get lines of the original output behind a 'gascoigne raw <id>' hint. "
                    + "Use grep (a regex) or lines (like 10-40) to ask for a part.")
    public String retrieveOriginal(
            @ToolParam(description = "the id from the hint") String rawId,
            @ToolParam(description = "regex matched per line", required = false) String grep,
            @ToolParam(description = "line range such as 10-40", required = false) String lines) {
        return gascoigne.retrieve(rawId, grep == null ? "" : grep, lines == null ? "" : lines);
    }
}
