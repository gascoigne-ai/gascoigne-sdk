"""Runtime state: one enum, one transition table, no flags (spec/protocol.md, Runtime states)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

BREAKER_FAILURES = 5
BREAKER_PAUSE = 60.0


class State(Enum):
    # Before the first call; the spec calls it "start".
    START = "start"
    # Never stored: derived from the environment on every call.
    OFF = "off"
    MISSING = "missing"
    STARTING = "starting"
    READY = "ready"
    PROTO_MISMATCH = "proto_mismatch"
    # Never stored: derived from READY and a reopen time still in the future.
    OPEN_UNTIL = "open_until"


class Event(Enum):
    FIRST_NATIVE = "first_native"
    FIRST_PROXY = "first_proxy"
    HEALTH_OK = "health_ok"
    HEALTH_MISMATCH = "health_mismatch"
    NO_CLI = "no_cli"
    START_FAILED = "start_failed"
    POLL_OK = "poll_ok"
    POLL_TIMEOUT = "poll_timeout"
    OPTIMIZE_OK = "optimize_ok"
    OPTIMIZE_FAILED = "optimize_failed"
    CLOSE = "close"


# (state, event) -> next state. Pairs not listed change nothing.
TRANSITIONS: dict[tuple[State, Event], State] = {
    (State.START, Event.FIRST_NATIVE): State.READY,
    (State.START, Event.FIRST_PROXY): State.STARTING,
    (State.STARTING, Event.HEALTH_OK): State.READY,
    (State.STARTING, Event.HEALTH_MISMATCH): State.PROTO_MISMATCH,
    (State.STARTING, Event.NO_CLI): State.MISSING,
    (State.STARTING, Event.START_FAILED): State.MISSING,
    (State.STARTING, Event.POLL_OK): State.READY,
    (State.STARTING, Event.POLL_TIMEOUT): State.MISSING,
    (State.READY, Event.OPTIMIZE_OK): State.READY,
    (State.READY, Event.OPTIMIZE_FAILED): State.READY,
    (State.READY, Event.CLOSE): State.MISSING,
}


@dataclass
class Machine:
    """The stored state plus the two counters the spec keeps beside it."""

    state: State = State.START
    # Consecutive optimize failures.
    failures: int = 0
    # Monotonic time the breaker reopens; 0 means no pause.
    reopen_at: float = 0.0
    # The one warning per runtime has been given.
    warned: bool = False

    def apply(self, event: Event, now: float) -> None:
        nxt = TRANSITIONS.get((self.state, event))
        if nxt is None:
            return
        self.state = nxt
        if event is Event.OPTIMIZE_OK:
            self.failures = 0
        elif event is Event.OPTIMIZE_FAILED:
            self.failures += 1
            if self.failures >= BREAKER_FAILURES:
                self.failures = 0
                self.reopen_at = now + BREAKER_PAUSE

    def at(self, now: float) -> State:
        """The state as seen at ``now``: READY with a future reopen time is OPEN_UNTIL."""
        if self.state is State.READY and now < self.reopen_at:
            return State.OPEN_UNTIL
        return self.state

    def first_warning(self) -> bool:
        """True once: the caller logs the warning only when this returns True."""
        if self.warned:
            return False
        self.warned = True
        return True
