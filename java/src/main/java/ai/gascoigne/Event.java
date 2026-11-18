package ai.gascoigne;

/** What can change the stored runtime state. */
enum Event {
    FIRST_NATIVE,
    FIRST_PROXY,
    HEALTH_OK,
    HEALTH_MISMATCH,
    NO_CLI,
    START_FAILED,
    POLL_OK,
    POLL_TIMEOUT,
    OPTIMIZE_OK,
    OPTIMIZE_FAILED,
    CLOSE
}
