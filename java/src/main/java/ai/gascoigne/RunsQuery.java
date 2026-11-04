package ai.gascoigne;

import java.time.Instant;

/**
 * Filters for {@link Gascoigne#runs}, newest first.
 *
 * @param before a run id: only older runs come back, to page; 0 for none
 * @param limit at most this many; 0 means 50, the most is 1000
 */
public record RunsQuery(
        String session, String agent, String model, Instant since, long before, int limit) {

    /** No filters. */
    public static final RunsQuery ALL = new RunsQuery(null, null, null, null, 0, 0);

    public static Builder builder() {
        return new Builder();
    }

    /** Builds a {@link RunsQuery}. */
    public static final class Builder {
        private String session;
        private String agent;
        private String model;
        private Instant since;
        private long before;
        private int limit;

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

        public Builder before(long before) {
            this.before = before;
            return this;
        }

        public Builder limit(int limit) {
            this.limit = limit;
            return this;
        }

        public RunsQuery build() {
            return new RunsQuery(session, agent, model, since, before, limit);
        }
    }
}
