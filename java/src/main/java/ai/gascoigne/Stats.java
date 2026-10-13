package ai.gascoigne;

/**
 * Tokens (estimated) before and after, summed over a client's calls.
 *
 * @param rawTokens before
 * @param outTokens after
 */
public record Stats(long rawTokens, long outTokens) {

    /** Fraction of tokens saved, 0 when nothing was optimized. */
    public double saved() {
        return rawTokens == 0 ? 0 : 1 - (double) outTokens / rawTokens;
    }
}
