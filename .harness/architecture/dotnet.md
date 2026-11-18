# .NET
Projects under `dotnet/src`; HTTP and JSON are built in.

| Zone | Files | Holds |
|---|---|---|
| core | `Gascoigne/Models.cs`, `GascoigneOptions.cs`, `EmbeddedSettings.cs`, `Selection.cs` | records, options, original selection |
| core + adapters (mixed) | `Gascoigne/GascoigneClient.cs` (482 lines) | breaker, warn-once, stats, HTTP calls, server spawn |
| adapter (native) | `Gascoigne/NativeEngine.cs` | P/Invoke binding to the library |
| helper | `Gascoigne.Extensions.AI` (`GascoigneFunctionInvocation`, `RetrieveOriginalFunction`) | Microsoft.Extensions.AI |
| data | `Gascoigne.Native/Bundle.cs` | bundled libraries |
