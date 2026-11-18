# Java
Module `java` (`jackson-databind`, `jna` optional); `java/spring-ai` is a separate module.

| Zone | Files | Holds |
|---|---|---|
| core | `Result`, `Stats`, `Total`, `Run`, `Attrs`, `TotalsQuery`, `RunsQuery`, `Settings`, `Selection` | records, query builders, original selection |
| core + adapters (mixed) | `Gascoigne.java` (512 lines) | breaker, warn-once, stats, `HttpClient` calls, `ProcessBuilder` spawn of the server, builder |
| wire (package-private) | `OptimizeRequest`, `Health` | protocol records |
| adapter (native) | `NativeEngine.java` | JNA binding to the library |
| helper | `java/spring-ai`: `GascoigneToolCallingManager`, `RetrieveOriginalTool`, `GascoigneConfiguration`, `EnableGascoigne` | Spring AI integration |
| module | `java/native` | bundle packaging |
