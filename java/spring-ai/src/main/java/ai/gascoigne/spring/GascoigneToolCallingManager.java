package ai.gascoigne.spring;

import ai.gascoigne.Attrs;
import ai.gascoigne.Gascoigne;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import org.springframework.ai.chat.messages.Message;
import org.springframework.ai.chat.messages.ToolResponseMessage;
import org.springframework.ai.chat.messages.ToolResponseMessage.ToolResponse;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.model.tool.ToolCallingChatOptions;
import org.springframework.ai.model.tool.ToolCallingManager;
import org.springframework.ai.model.tool.ToolExecutionResult;
import org.springframework.ai.tool.definition.ToolDefinition;

/**
 * Runs the real tool calls, then shortens the text each tool returned before the model reads it.
 * Every tool goes through {@link ToolCallingManager}, so this one wrapper covers them all.
 */
public final class GascoigneToolCallingManager implements ToolCallingManager {
    private static final ObjectMapper JSON = new ObjectMapper();

    private final ToolCallingManager delegate;
    private final Gascoigne gascoigne;
    private final Set<String> skip;
    private final int minChars;

    /**
     * Creates the decorator.
     *
     * @param delegate the manager that runs the tools
     * @param gascoigne the client results are optimized with
     * @param skip names of tools never touched
     * @param minChars results shorter than this are left alone
     */
    public GascoigneToolCallingManager(
            ToolCallingManager delegate, Gascoigne gascoigne, Set<String> skip, int minChars) {
        this.delegate = delegate;
        this.gascoigne = gascoigne;
        this.skip = skip;
        this.minChars = minChars;
    }

    @Override
    public List<ToolDefinition> resolveToolDefinitions(ToolCallingChatOptions options) {
        return delegate.resolveToolDefinitions(options);
    }

    @Override
    public ToolExecutionResult executeToolCalls(Prompt prompt, ChatResponse response) {
        ToolExecutionResult result = delegate.executeToolCalls(prompt, response);
        List<Message> history = new ArrayList<>(result.conversationHistory());
        int last = history.size() - 1;
        if (last >= 0 && history.get(last) instanceof ToolResponseMessage message) {
            history.set(last, shorten(message));
        }
        return ToolExecutionResult.builder()
                .conversationHistory(history)
                .returnDirect(result.returnDirect())
                .build();
    }

    private ToolResponseMessage shorten(ToolResponseMessage message) {
        List<ToolResponse> responses = message.getResponses().stream()
                .map(r -> new ToolResponse(r.id(), r.name(), shorten(r.name(), r.responseData())))
                .toList();
        return new ToolResponseMessage(responses, message.getMetadata());
    }

    /** Tool results arrive as JSON; a string result is unquoted so line structure is visible. */
    private String shorten(String tool, String responseData) {
        if (skip.contains(tool) || responseData == null || responseData.length() < minChars) {
            return responseData;
        }
        try {
            JsonNode node = JSON.readTree(responseData);
            if (node.isTextual()) {
                String text = node.asText();
                return text.contains("full: gascoigne raw")
                        ? responseData
                        : JSON.writeValueAsString(gascoigne.optimize(text, Attrs.tool(tool)));
            }
        } catch (JsonProcessingException e) {
            // Not JSON: treat the data as plain text below.
        }
        return gascoigne.optimize(responseData, Attrs.tool(tool));
    }
}
