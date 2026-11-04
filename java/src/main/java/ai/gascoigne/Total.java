package ai.gascoigne;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * The recorded runs of one group, summed.
 *
 * @param group what the runs were grouped by, e.g. an agent or a day
 * @param runs runs in the group
 * @param optimized runs that were shortened
 * @param failed runs whose optimizer failed
 * @param rawTokens estimated tokens before
 * @param outTokens estimated tokens after
 * @param saved {@code rawTokens - outTokens}
 * @param first RFC 3339 time of the first run, empty when unknown
 * @param last RFC 3339 time of the last run, empty when unknown
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record Total(
        @JsonProperty("group") String group,
        @JsonProperty("runs") long runs,
        @JsonProperty("optimized") long optimized,
        @JsonProperty("failed") long failed,
        @JsonProperty("raw_tokens") long rawTokens,
        @JsonProperty("out_tokens") long outTokens,
        @JsonProperty("saved") long saved,
        @JsonProperty("first") String first,
        @JsonProperty("last") String last) {

    public Total {
        group = group == null ? "" : group;
        first = first == null ? "" : first;
        last = last == null ? "" : last;
    }
}
