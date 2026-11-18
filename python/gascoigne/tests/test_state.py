import pytest
from gascoigne.state import BREAKER_FAILURES, BREAKER_PAUSE, Event, Machine, State

NOW = 1000.0


# (from, event, failures before) -> (to, failures after, reopen_at after)
TRANSITIONS = [
    (State.START, Event.FIRST_NATIVE, 0, State.READY, 0, 0.0),
    (State.START, Event.FIRST_PROXY, 0, State.STARTING, 0, 0.0),
    (State.STARTING, Event.HEALTH_OK, 0, State.READY, 0, 0.0),
    (State.STARTING, Event.HEALTH_MISMATCH, 0, State.PROTO_MISMATCH, 0, 0.0),
    (State.STARTING, Event.NO_CLI, 0, State.MISSING, 0, 0.0),
    (State.STARTING, Event.START_FAILED, 0, State.MISSING, 0, 0.0),
    (State.STARTING, Event.POLL_OK, 0, State.READY, 0, 0.0),
    (State.STARTING, Event.POLL_TIMEOUT, 0, State.MISSING, 0, 0.0),
    (State.READY, Event.OPTIMIZE_OK, 3, State.READY, 0, 0.0),
    (State.READY, Event.OPTIMIZE_FAILED, 0, State.READY, 1, 0.0),
    (
        State.READY,
        Event.OPTIMIZE_FAILED,
        BREAKER_FAILURES - 2,
        State.READY,
        BREAKER_FAILURES - 1,
        0.0,
    ),
    (State.READY, Event.OPTIMIZE_FAILED, BREAKER_FAILURES - 1, State.READY, 0, NOW + BREAKER_PAUSE),
    (State.READY, Event.CLOSE, 2, State.MISSING, 2, 0.0),
    # events that do not apply to a state change nothing
    (State.MISSING, Event.OPTIMIZE_FAILED, 0, State.MISSING, 0, 0.0),
    (State.PROTO_MISMATCH, Event.HEALTH_OK, 0, State.PROTO_MISMATCH, 0, 0.0),
    (State.START, Event.OPTIMIZE_OK, 0, State.START, 0, 0.0),
]


@pytest.mark.parametrize(
    ("src", "event", "failures", "dst", "failures_after", "reopen"), TRANSITIONS
)
def test_transition_table(src, event, failures, dst, failures_after, reopen):
    m = Machine(state=src, failures=failures)
    m.apply(event, NOW)
    assert (m.state, m.failures, m.reopen_at) == (dst, failures_after, reopen)


def test_open_until_derives_from_reopen_time():
    m = Machine(state=State.READY, failures=BREAKER_FAILURES - 1)
    m.apply(Event.OPTIMIZE_FAILED, NOW)
    assert m.at(NOW) is State.OPEN_UNTIL
    assert m.at(NOW + BREAKER_PAUSE - 0.1) is State.OPEN_UNTIL
    assert m.at(NOW + BREAKER_PAUSE) is State.READY
    # five more failures are needed to reopen
    m.apply(Event.OPTIMIZE_FAILED, NOW + BREAKER_PAUSE)
    assert m.at(NOW + BREAKER_PAUSE) is State.READY


def test_warning_is_once_per_machine():
    m = Machine()
    assert m.first_warning()
    assert not m.first_warning()
