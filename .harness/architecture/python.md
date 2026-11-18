# Python
Package `python/gascoigne/src/gascoigne`; approved dependency: `httpx`.

| Zone | Files | Holds |
|---|---|---|
| core | `models.py` | wire dataclasses (`OptimizeRequest`, `Result`, `Run`, `Stats`, `Total`) |
| core | `retrieve.py` | `select`: grep or line range over an original |
| core | `state.py` | `State`, `Event`, `TRANSITIONS`, `Machine` (stored state, breaker counters, warn-once flag) |
| core + composition | `runtime.py` | `Runtime`: owns the lock, the `Machine` and the stats; picks native or HTTP; module functions over a default instance |
| adapter (HTTP) | `http.py` | `health` and `ServerClient`: `/sdk/v1` requests; raise, `Runtime` absorbs |
| adapter (process) | `process.py` | `find_cli`, `start_server`: locate and start the CLI server |
| adapter (native) | `native.py` | ctypes loader, `Settings`, `NativeError`; `Runtime` catches it |
| helper | `auto.py` | opt-in, reversible `auto()` patches of installed libraries |
| helper | `ext/langchain.py` | `optimize_tools` wraps StructuredTool callables |
| data | `python/gascoigne-native` | bundled libraries, `LIB_DIR` only, no code |

`__init__.py` is the public surface. `Runtime` stays the composition point: adapters never import
each other, and `http.py` returns the protocol number so `Runtime` decides on a mismatch.
