# Python
Package `python/gascoigne/src/gascoigne`; approved dependency: `httpx`.

| Zone | Files | Holds |
|---|---|---|
| core | `models.py` | wire dataclasses (`OptimizeRequest`, `Result`, `Run`, `Stats`, `Total`) |
| core | `retrieve.py` | `select`: grep or line range over an original |
| core + adapters (mixed) | `runtime.py` | `Runtime`: see "Known mixing" in `../architecture.md`; module functions over a default instance |
| adapter (native) | `native.py` | ctypes loader, `Settings`, `NativeError`; `Runtime` catches it |
| helper | `auto.py` | opt-in, reversible `auto()` patches of installed libraries |
| helper | `ext/langchain.py` | `optimize_tools` wraps StructuredTool callables |
| data | `python/gascoigne-native` | bundled libraries, `LIB_DIR` only, no code |

`__init__.py` is the public surface. Target: task 007.
