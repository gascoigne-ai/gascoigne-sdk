# gascoigne-native

Adds the native variant to the `gascoigne` SDK: the engine runs inside your Python process, with no
server and no CLI. Install it next to the SDK and select it:

```python
import gascoigne

gascoigne.init(mode="native")
```

The library for your platform is unpacked to the temporary directory on first use. See
`spec/native.md` in the repository for the layout and the environment variables.
