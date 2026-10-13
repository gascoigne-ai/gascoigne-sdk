package ai.gascoigne;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * One optimize call.
 *
 * @param text what the model should read
 * @param rawId id of the stored original, see {@link Gascoigne#raw(String)}; empty when unchanged
 * @param rawTokens estimated tokens before
 * @param outTokens estimated tokens after
 * @param skipped why nothing was optimized, empty otherwise
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record Result(
        @JsonProperty("text") String text,
        @JsonProperty("raw_id") String rawId,
        @JsonProperty("raw_tokens") long rawTokens,
        @JsonProperty("out_tokens") long outTokens,
        @JsonProperty("skipped") String skipped) {

    /** The input, unchanged. */
    static Result unchanged(String text) {
        return new Result(text, "", 0, 0, "");
    }
}
