package ai.gascoigne.demo.springai.wrap;

import ai.gascoigne.Attrs;
import ai.gascoigne.Gascoigne;
import ai.gascoigne.demo.Demo;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.stereotype.Component;

/** The tool the model can call. */
@Component
class LogTools {
    private final Gascoigne gascoigne;

    LogTools(Gascoigne gascoigne) {
        this.gascoigne = gascoigne;
    }

    @Tool(name = "search_logs", description = "Return the recent service logs.")
    String searchLogs() {
        // 2. Optimize what the tool returns.
        return gascoigne.optimize(Demo.noisyLogs(), Attrs.tool("search_logs"));
    }
}
