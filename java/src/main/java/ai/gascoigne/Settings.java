package ai.gascoigne;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * Configuration for the embedded engine. The library merges it over its built-in defaults and the
 * user's config file; nothing is merged on the Java side (see spec/native.md).
 *
 * @param config YAML laid over the defaults and the user's file
 * @param set "dotted.path=value" assignments applied last
 * @param only keeps just these optimizers in every chain
 * @param disable drops these optimizers from every chain
 * @param ignoreUserFile skips the user's config file
 * @param timeoutMs per-call bound inside the library, 0 for its default
 * @param ledger "file" (default: the configured sqlite file) or "memory" (private to this process)
 * @param pricing prices behind {@link Gascoigne#costs}
 */
@JsonInclude(JsonInclude.Include.NON_DEFAULT)
public record Settings(
        @JsonProperty("config") String config,
        @JsonProperty("set") List<String> set,
        @JsonProperty("only") List<String> only,
        @JsonProperty("disable") List<String> disable,
        @JsonProperty("ignore_user_file") boolean ignoreUserFile,
        @JsonProperty("timeout_ms") int timeoutMs,
        @JsonProperty("ledger") String ledger,
        @JsonProperty("pricing") Pricing pricing) {

    /** Defaults only. */
    public static Settings defaults() {
        return new Settings(null, null, null, null, false, 0, null, null);
    }

    /** These defaults with {@code yaml} laid over them. */
    public Settings withConfig(String yaml) {
        return new Settings(yaml, set, only, disable, ignoreUserFile, timeoutMs, ledger, pricing);
    }

    /** These settings without the user's config file. */
    public Settings withoutUserFile() {
        return new Settings(config, set, only, disable, true, timeoutMs, ledger, pricing);
    }

    /** These settings with the ledger kept in "memory" (or "file", the default). */
    public Settings withLedger(String mode) {
        return new Settings(config, set, only, disable, ignoreUserFile, timeoutMs, mode, pricing);
    }

    /** These settings with the prices behind {@link Gascoigne#costs}. */
    public Settings withPricing(Pricing value) {
        return new Settings(config, set, only, disable, ignoreUserFile, timeoutMs, ledger, value);
    }
}
