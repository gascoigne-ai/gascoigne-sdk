package ai.gascoigne;

import com.fasterxml.jackson.annotation.JsonInclude;

/** Body of {@code POST /sdk/v1/optimize}; empty fields are not sent. */
@JsonInclude(JsonInclude.Include.NON_EMPTY)
record OptimizeRequest(
        String text, String agent, String session, String tool, String cmd, String url, String query, String model) {

    static OptimizeRequest of(String text, String agent, String session, Attrs attrs) {
        return new OptimizeRequest(
                text, agent, session, attrs.tool(), attrs.cmd(), attrs.url(), attrs.query(), attrs.model());
    }
}
