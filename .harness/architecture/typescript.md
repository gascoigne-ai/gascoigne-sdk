# TypeScript
Packages under `typescript/packages`; HTTP is built in, `koffi` optional (embedded mode).

| Zone | Files | Holds |
|---|---|---|
| core | `sdk/src/index.ts` (types) | `Result`, `Attrs`, `Stats`, `Total`, `Run`, `Health`, unions `Outcome`, `Route` (unknown strings allowed), query types, wire request/response |
| core | `sdk/src/index.ts` (decoders) | `decodeHealth`, `decodeResult`, `decodeTotals`, `decodeRuns`: wire JSON to typed values, throw on a bad body |
| core + adapters (mixed) | `sdk/src/index.ts` (`Runtime`) | breaker, warn-once, stats, `fetch` calls, `startServer` spawn; module functions over `current` |
| adapter (native) | `sdk/src/native.ts` | koffi loader, `Settings`, `NativeError`, bundle unpack |
| helper | `ai-sdk/src/index.ts` | wraps AI SDK tools |
| data | `typescript/native-template` | template for per-platform bundle packages |
