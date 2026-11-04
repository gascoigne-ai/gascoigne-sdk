package ai.gascoigne;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * One recorded optimization.
 *
 * @param id run id, for paging with {@link RunsQuery#before()}
 * @param time RFC 3339
 * @param rawId id of the stored original, see {@link Gascoigne#raw(String)}
 * @param outcome optimized, unchanged, bypassed, rerequested or error
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record Run(
        @JsonProperty("id") long id,
        @JsonProperty("time") String time,
        @JsonProperty("session") String session,
        @JsonProperty("agent") String agent,
        @JsonProperty("model") String model,
        @JsonProperty("command") String command,
        @JsonProperty("route") String route,
        @JsonProperty("optimizers") List<String> optimizers,
        @JsonProperty("raw_tokens") long rawTokens,
        @JsonProperty("out_tokens") long outTokens,
        @JsonProperty("duration_ns") long durationNs,
        @JsonProperty("raw_id") String rawId,
        @JsonProperty("outcome") String outcome,
        @JsonProperty("reason") String reason) {

    public Run {
        time = time == null ? "" : time;
        session = session == null ? "" : session;
        agent = agent == null ? "" : agent;
        model = model == null ? "" : model;
        command = command == null ? "" : command;
        route = route == null ? "" : route;
        optimizers = optimizers == null ? List.of() : List.copyOf(optimizers);
        rawId = rawId == null ? "" : rawId;
        outcome = outcome == null ? "" : outcome;
        reason = reason == null ? "" : reason;
    }
}
