package ai.gascoigne.demo.springai.proxy;

import ai.gascoigne.demo.Demo;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.stereotype.Component;

/** A tool with no gascoigne code in it. */
@Component
class LogTools {

    @Tool(name = "search_logs", description = "Return the recent service logs.")
    String searchLogs() {
        return Demo.noisyLogs();
    }
}
