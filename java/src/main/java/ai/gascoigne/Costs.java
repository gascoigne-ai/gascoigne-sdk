package ai.gascoigne;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * What the tokens saved are worth: an estimate from list prices or the prices configured for
 * gascoigne, not what anyone is billed. With {@code billing} "subscription" there are no dollars.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record Costs(
        @JsonProperty("billing") String billing,
        @JsonProperty("first_read_usd") double firstReadUsd,
        @JsonProperty("in_context_usd") double inContextUsd,
        @JsonProperty("rereads") double rereads,
        @JsonProperty("savings") List<ModelCost> savings,
        @JsonProperty("unpriced") List<String> unpriced) {

    /** What a failed read returns. */
    static final Costs EMPTY = new Costs("", 0, 0, 0, null, null);

    public Costs {
        billing = billing == null ? "" : billing;
        savings = savings == null ? List.of() : List.copyOf(savings);
        unpriced = unpriced == null ? List.of() : List.copyOf(unpriced);
    }
}
