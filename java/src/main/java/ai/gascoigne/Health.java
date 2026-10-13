package ai.gascoigne;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/** Response of {@code GET /sdk/v1/health}. */
@JsonIgnoreProperties(ignoreUnknown = true)
record Health(String version, int proto) {}
