# Java
Module `java` (`jackson-databind`, `jna` optional); `java/spring-ai` is a separate module.

| Zone | Files | Holds |
|---|---|---|
| core | `Result`, `Stats`, `Total`, `Run`, `Attrs`, `TotalsQuery`, `RunsQuery`, `Settings`, `Selection` | records, query builders, original selection |
| core (package-private) | `State`, `Event`, `Machine` | state enum, event enum, transition table, breaker counters and warn-once flag |
| core + adapters (mixed) | `Gascoigne.java` (527 lines) | delegates runtime state to `Machine`; stats, `HttpClient` calls, `ProcessBuilder` spawn of the server, builder |
| wire (package-private) | `OptimizeRequest`, `Health` | protocol records |
| adapter (native) | `NativeEngine.java` | JNA binding to the library |
| helper | `java/spring-ai`: `GascoigneToolCallingManager`, `RetrieveOriginalTool`, `GascoigneConfiguration`, `EnableGascoigne` | Spring AI integration |
| module | `java/native` | bundle packaging |
