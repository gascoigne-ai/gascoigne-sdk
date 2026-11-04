package ai.gascoigne;

import java.time.Instant;

/**
 * Filters for {@link Gascoigne#totals} and {@link Gascoigne#costs}. Null or empty fields match
 * everything.
 *
 * @param by route (default), session, family, optimizer, command, outcome, agent, model, day,
 *     week or month; totals only
 * @param since only runs from this time on
 */
public record TotalsQuery(String by, String session, String agent, String model, Instant since) {

    /** No filters. */
    public static final TotalsQuery ALL = new TotalsQuery(null, null, null, null, null);

    public static Builder builder() {
        return new Builder();
    }

    /** Builds a {@link TotalsQuery}. */
    public static final class Builder {
        private String by;
        private String session;
        private String agent;
        private String model;
        private Instant since;

        public Builder by(String by) {
            this.by = by;
            return this;
        }

        public Builder session(String session) {
            this.session = session;
            return this;
        }

        public Builder agent(String agent) {
            this.agent = agent;
            return this;
        }

        public Builder model(String model) {
            this.model = model;
            return this;
        }

        public Builder since(Instant since) {
            this.since = since;
            return this;
        }

        public TotalsQuery build() {
            return new TotalsQuery(by, session, agent, model, since);
        }
    }
}
