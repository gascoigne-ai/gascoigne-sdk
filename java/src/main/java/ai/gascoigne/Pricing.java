package ai.gascoigne;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

/**
 * Where dollar figures come from for the embedded engine. Prices are held per process, not per
 * client.
 *
 * @param billing "api" (default) or "subscription": a flat plan has no dollars
 * @param prices static prices by model id
 * @param file a price sheet (JSON) read once when the engine opens
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record Pricing(
        @JsonProperty("billing") String billing,
        @JsonProperty("prices") Map<String, Price> prices,
        @JsonProperty("file") String file) {}
