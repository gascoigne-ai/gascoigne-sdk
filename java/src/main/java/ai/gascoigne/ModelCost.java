package ai.gascoigne;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * The tokens saved, priced for one model.
 *
 * @param source where the price comes from: built-in, static, json, api or script
 * @param tokens saved, in gascoigne's estimate units
 * @param modelTokens saved, in the model's own tokens
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record ModelCost(
        @JsonProperty("model") String model,
        @JsonProperty("source") String source,
        @JsonProperty("assumed") boolean assumed,
        @JsonProperty("tokenizer") String tokenizer,
        @JsonProperty("tokens") long tokens,
        @JsonProperty("model_tokens") long modelTokens,
        @JsonProperty("first_read_usd") double firstReadUsd,
        @JsonProperty("in_context_usd") double inContextUsd) {

    public ModelCost {
        model = model == null ? "" : model;
        source = source == null ? "" : source;
        tokenizer = tokenizer == null ? "" : tokenizer;
    }
}
