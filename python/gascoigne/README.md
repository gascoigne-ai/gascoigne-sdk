# gascoigne (Python)

```python
import gascoigne

gascoigne.init(agent="my-app")
short = gascoigne.optimize(tool_output, tool="grep")  # unchanged if gascoigne is unavailable


@gascoigne.wrap_tool  # any callable returning str
def run_tests() -> str: ...
```

Needs the `gascoigne` CLI on `PATH`; without it the SDK logs one warning and passes everything through.
