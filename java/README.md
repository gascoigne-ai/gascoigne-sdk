# gascoigne (Java)

Optimize tool results before your model reads them. Without the `gascoigne` CLI on `PATH` it logs one warning and returns inputs unchanged.

```java
var g = Gascoigne.builder().agent("my-agent").build();
String shortText = g.optimize(toolOutput, Gascoigne.Attrs.tool("grep"));
Function<String,String> wrapped = g.wrapTool("search", searchFn);   // LangChain4j / Spring AI tool bodies
```

