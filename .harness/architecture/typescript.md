# TypeScript
Packages under `typescript/packages`; HTTP is built in, `koffi` optional (embedded mode).

| Zone | Files | Holds |
|---|---|---|
| core | `sdk/src/index.ts` (types) | `Result`, `Attrs`, `Stats`, `Total`, `Run`, query types, wire request/response |
| core + adapters (mixed) | `sdk/src/index.ts` (`Runtime`) | breaker, warn-once, stats, `fetch` calls, `startServer` spawn; module functions over `current` |
| adapter (native) | `sdk/src/native.ts` | koffi loader, `Settings`, `NativeError`, bundle unpack |
| helper | `ai-sdk/src/index.ts` | wraps AI SDK tools |
| data | `typescript/native-template` | template for per-platform bundle packages |
