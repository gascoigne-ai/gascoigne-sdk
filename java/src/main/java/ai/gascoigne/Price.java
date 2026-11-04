package ai.gascoigne;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * One model's price, dollars per million tokens.
 *
 * @param in required
 * @param out required
 * @param cacheRead null means {@code in}
 * @param cacheWrite null means {@code in}
 * @param tokenizer o200k (null means this), claude, claude-legacy or gemini
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record Price(
        @JsonProperty("in") double in,
        @JsonProperty("out") double out,
        @JsonProperty("cache_read") Double cacheRead,
        @JsonProperty("cache_write") Double cacheWrite,
        @JsonProperty("tokenizer") String tokenizer) {}
