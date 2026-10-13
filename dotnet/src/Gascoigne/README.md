# Gascoigne (.NET)

Optimize tool results before your model reads them. Without the `gascoigne` CLI on `PATH` it logs one
warning and returns inputs unchanged.

```csharp
var g = new GascoigneClient(new GascoigneOptions { Agent = "my-agent" });
string shortText = await g.OptimizeAsync(toolOutput, new Attrs { Tool = "grep" });
var wrapped = g.WrapTool("search", SearchAsync);   // Semantic Kernel / Microsoft.Extensions.AI tool bodies
```
