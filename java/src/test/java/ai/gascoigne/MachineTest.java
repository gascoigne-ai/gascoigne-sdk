package ai.gascoigne;

import static ai.gascoigne.Machine.BREAKER_FAILURES;
import static ai.gascoigne.Machine.BREAKER_PAUSE_NANOS;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

class MachineTest {
    private static final long NOW = 1000;

    private record Row(State from, Event event, int failures, State to, int failuresAfter,
            long reopenAt) {}

    // (from, event, failures before) -> (to, failures after, reopen_at after)
    private static final List<Row> TRANSITIONS = List.of(
            new Row(State.START, Event.FIRST_NATIVE, 0, State.READY, 0, 0),
            new Row(State.START, Event.FIRST_PROXY, 0, State.STARTING, 0, 0),
            new Row(State.STARTING, Event.HEALTH_OK, 0, State.READY, 0, 0),
            new Row(State.STARTING, Event.HEALTH_MISMATCH, 0, State.PROTO_MISMATCH, 0, 0),
            new Row(State.STARTING, Event.NO_CLI, 0, State.MISSING, 0, 0),
            new Row(State.STARTING, Event.START_FAILED, 0, State.MISSING, 0, 0),
            new Row(State.STARTING, Event.POLL_OK, 0, State.READY, 0, 0),
            new Row(State.STARTING, Event.POLL_TIMEOUT, 0, State.MISSING, 0, 0),
            new Row(State.READY, Event.OPTIMIZE_OK, 3, State.READY, 0, 0),
            new Row(State.READY, Event.OPTIMIZE_FAILED, 0, State.READY, 1, 0),
            new Row(State.READY, Event.OPTIMIZE_FAILED, BREAKER_FAILURES - 2, State.READY,
                    BREAKER_FAILURES - 1, 0),
            new Row(State.READY, Event.OPTIMIZE_FAILED, BREAKER_FAILURES - 1, State.READY, 0,
                    NOW + BREAKER_PAUSE_NANOS),
            new Row(State.READY, Event.CLOSE, 2, State.MISSING, 2, 0),
            // events that do not apply to a state change nothing
            new Row(State.MISSING, Event.OPTIMIZE_FAILED, 0, State.MISSING, 0, 0),
            new Row(State.PROTO_MISMATCH, Event.HEALTH_OK, 0, State.PROTO_MISMATCH, 0, 0),
            new Row(State.START, Event.OPTIMIZE_OK, 0, State.START, 0, 0));

    @Test void transitionTable() {
        for (Row row : TRANSITIONS) {
            Machine m = new Machine(row.from(), row.failures());
            m.apply(row.event(), NOW);
            String label = row.from() + " + " + row.event();
            assertEquals(row.to(), m.state(), label);
            assertEquals(row.failuresAfter(), m.failures(), label);
            assertEquals(row.reopenAt(), m.reopenAt(), label);
        }
    }

    @Test void openUntilDerivesFromReopenTime() {
        Machine m = new Machine(State.READY, BREAKER_FAILURES - 1);
        m.apply(Event.OPTIMIZE_FAILED, NOW);
        assertEquals(State.OPEN_UNTIL, m.at(NOW));
        assertEquals(State.OPEN_UNTIL, m.at(NOW + BREAKER_PAUSE_NANOS - 1));
        assertEquals(State.READY, m.at(NOW + BREAKER_PAUSE_NANOS));
        // five more failures are needed to reopen
        m.apply(Event.OPTIMIZE_FAILED, NOW + BREAKER_PAUSE_NANOS);
        assertEquals(State.READY, m.at(NOW + BREAKER_PAUSE_NANOS));
    }

    @Test void warningIsOncePerMachine() {
        Machine m = new Machine(State.START, 0);
        assertTrue(m.firstWarning());
        assertFalse(m.firstWarning());
    }
}
