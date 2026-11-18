package ai.gascoigne;

import java.util.Map;

/** The stored state plus the counters the spec keeps beside it. Not thread safe; callers lock. */
final class Machine {
    static final int BREAKER_FAILURES = 5;
    static final long BREAKER_PAUSE_NANOS = 60_000_000_000L;

    private record Key(State state, Event event) {}

    // (state, event) -> next state. Pairs not listed change nothing.
    private static final Map<Key, State> TRANSITIONS = Map.ofEntries(
            Map.entry(new Key(State.START, Event.FIRST_NATIVE), State.READY),
            Map.entry(new Key(State.START, Event.FIRST_PROXY), State.STARTING),
            Map.entry(new Key(State.STARTING, Event.HEALTH_OK), State.READY),
            Map.entry(new Key(State.STARTING, Event.HEALTH_MISMATCH), State.PROTO_MISMATCH),
            Map.entry(new Key(State.STARTING, Event.NO_CLI), State.MISSING),
            Map.entry(new Key(State.STARTING, Event.START_FAILED), State.MISSING),
            Map.entry(new Key(State.STARTING, Event.POLL_OK), State.READY),
            Map.entry(new Key(State.STARTING, Event.POLL_TIMEOUT), State.MISSING),
            Map.entry(new Key(State.READY, Event.OPTIMIZE_OK), State.READY),
            Map.entry(new Key(State.READY, Event.OPTIMIZE_FAILED), State.READY),
            Map.entry(new Key(State.READY, Event.CLOSE), State.MISSING));

    private State state;
    // Consecutive optimize failures.
    private int failures;
    // System.nanoTime() the breaker reopens; 0 means no pause.
    private long reopenAt;
    // The one warning per runtime has been given.
    private boolean warned;

    Machine() {
        this(State.START, 0);
    }

    Machine(State state, int failures) {
        this.state = state;
        this.failures = failures;
    }

    State state() {
        return state;
    }

    int failures() {
        return failures;
    }

    long reopenAt() {
        return reopenAt;
    }

    void apply(Event event, long now) {
        State next = TRANSITIONS.get(new Key(state, event));
        if (next == null) {
            return;
        }
        state = next;
        if (event == Event.OPTIMIZE_OK) {
            failures = 0;
        } else if (event == Event.OPTIMIZE_FAILED && ++failures >= BREAKER_FAILURES) {
            failures = 0;
            reopenAt = now + BREAKER_PAUSE_NANOS;
        }
    }

    /** The state as seen at {@code now}: READY with a future reopen time is OPEN_UNTIL. */
    State at(long now) {
        if (state == State.READY && reopenAt != 0 && now - reopenAt < 0) {
            return State.OPEN_UNTIL;
        }
        return state;
    }

    /** True once: the caller logs the warning only when this returns true. */
    boolean firstWarning() {
        if (warned) {
            return false;
        }
        warned = true;
        return true;
    }
}
