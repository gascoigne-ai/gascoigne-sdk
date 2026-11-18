package ai.gascoigne;

/** Runtime state (spec/protocol.md, Runtime states). */
enum State {
    /** Before the first call; the spec calls it "start". */
    START,
    /** Never stored: derived from the environment on every call. */
    OFF,
    MISSING,
    STARTING,
    READY,
    PROTO_MISMATCH,
    /** Never stored: derived from READY and a reopen time still in the future. */
    OPEN_UNTIL
}
