package ai.gascoigne.demo;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/** One run recorded by the gascoigne server, as {@code GET /api/events} lists it. */
@JsonIgnoreProperties(ignoreUnknown = true)
record ProxyEvent(
        @JsonProperty("id") long id,
        @JsonProperty("pipeline") String pipeline,
        @JsonProperty("route") String route,
        @JsonProperty("command") String command,
        @JsonProperty("raw_tokens") long rawTokens,
        @JsonProperty("out_tokens") long outTokens,
        @JsonProperty("raw_id") String rawId) {}
