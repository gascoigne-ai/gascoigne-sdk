"""The embedded variant: the gascoigne engine as a shared library, called through ctypes.

See spec/native.md. Nothing here raises into the host app except `NativeError`, which `Runtime`
catches at its boundary.
"""

from __future__ import annotations

import ctypes
import gzip
import hashlib
import json
import os
import platform
import sys
import tempfile
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path

from gascoigne.models import OptimizeRequest, Result, Run, Total

ABI = 3


class NativeError(Exception):
    """The library is missing, has another ABI, or reported a failure."""


@dataclass(frozen=True)
class Settings:
    """Configuration sent to the library, which merges it over its defaults and the user's file."""

    # YAML laid over the defaults and the user's file
    config: str = ""
    # "dotted.path=value" assignments applied last
    set: list[str] = field(default_factory=lambda: list[str]())
    only: list[str] = field(default_factory=lambda: list[str]())
    disable: list[str] = field(default_factory=lambda: list[str]())
    ignore_user_file: bool = False
    timeout_ms: int = 0
    # "file" (default: the configured sqlite file) or "memory" (private to this process)
    ledger: str = ""

    def to_json(self) -> str:
        return json.dumps({k: v for k, v in asdict(self).items() if v})


def _names() -> list[str]:
    if sys.platform == "win32":
        return ["gascoigne.dll"]
    if sys.platform == "darwin":
        return ["libgascoigne.dylib"]
    return ["libgascoigne.so"]


def platform_key() -> str:
    """`<os>-<arch>` as the bundle names its folders."""
    system = {"linux": "linux", "darwin": "darwin", "win32": "windows"}.get(sys.platform, "")
    machine = platform.machine().lower()
    arch = {"x86_64": "amd64", "amd64": "amd64", "arm64": "arm64", "aarch64": "arm64"}.get(machine)
    return f"{system}-{arch}"


def unpack(bundled: Path) -> Path:
    """Unpack a gzip-compressed library into the temp directory and return the file to load.

    The folder is named by the library's hash, so unpacking is idempotent and an existing file is
    trusted only when its content matches. The write goes through a temporary name and a rename.
    """
    data = gzip.decompress(bundled.read_bytes())
    digest = hashlib.sha256(data).hexdigest()[:16]
    root = Path(os.environ.get("GASCOIGNE_LIB_DIR") or tempfile.gettempdir())
    folder = root / f"gascoigne-native-{digest}"
    target = folder / bundled.name.removesuffix(".gz")
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest()[:16] == digest:
        return target
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    partial = folder / f".{os.getpid()}.{target.name}.tmp"
    partial.write_bytes(data)
    partial.chmod(0o700)
    partial.replace(target)
    return target


def bundled_library() -> Path | None:
    """This platform's entry of the gascoigne-native bundle, or None when it is not installed."""
    try:
        from gascoigne_native import LIB_DIR
    except ImportError:
        return None
    entries = sorted((LIB_DIR / platform_key()).glob("*.gz"))
    return entries[0] if entries else None


def system_dirs() -> list[Path]:
    """Where an installed library may live: `$GASCOIGNE_LIB_PATH`, the CLI's dir, then the
    conventional places of the platform (see spec/native.md)."""
    dirs = [Path(d) for d in os.environ.get("GASCOIGNE_LIB_PATH", "").split(os.pathsep) if d]
    if os.environ.get("GASCOIGNE_BIN"):
        dirs.append(Path(os.environ["GASCOIGNE_BIN"]).parent)
    home = Path.home()
    if sys.platform == "win32":
        for var in ("LOCALAPPDATA", "ProgramFiles"):
            if os.environ.get(var):
                dirs.append(Path(os.environ[var]) / "gascoigne")
    elif sys.platform == "darwin":
        dirs += [home / ".local/lib", Path("/usr/local/lib"), Path("/opt/homebrew/lib")]
    else:
        multiarch = f"{platform.machine()}-linux-gnu"
        dirs += [
            home / ".local/lib",
            Path("/usr/local/lib"),
            Path("/usr/lib"),
            Path("/usr/lib64"),
            Path("/usr/lib") / multiarch,
            Path("/opt/gascoigne/lib"),
        ]
    return dirs


def find_library() -> tuple[Path | None, list[str]]:
    """The library to load and where was looked, in order: `$GASCOIGNE_LIB`, the system
    directories, then the gascoigne-native dependency unpacked to a temp directory."""
    looked: list[str] = []
    env = os.environ.get("GASCOIGNE_LIB")
    if env:
        looked.append(f"$GASCOIGNE_LIB={env}")
        return (Path(env), looked) if Path(env).is_file() else (None, looked)
    for directory in system_dirs():
        looked.append(str(directory))
        for name in _names():
            if (directory / name).is_file():
                return directory / name, looked
    if os.environ.get("GASCOIGNE_UNPACK") != "off":
        looked.append("the gascoigne-native package")
        bundled = bundled_library()
        if bundled is not None:
            return unpack(bundled), looked
    return None, looked


class Native:
    """An open engine in this process. Thread-safe: the library serializes calls itself."""

    def __init__(self, settings: Settings, path: Path | None = None) -> None:
        looked: list[str] = []
        lib_path = path
        if lib_path is None:
            lib_path, looked = find_library()
        if lib_path is None:
            raise NativeError(
                "libgascoigne not found; looked in: "
                + ", ".join(looked)
                + ". Install it in one of those places or add the gascoigne-native package"
            )
        try:
            lib = ctypes.CDLL(str(lib_path))
        except OSError as e:
            raise NativeError(f"cannot load {lib_path}: {e}") from e
        self._lib = _bind(lib)
        if self._lib.gascoigne_abi_version() != ABI:
            raise NativeError(f"{lib_path} speaks another ABI than {ABI}")
        self._lock = threading.Lock()
        self._handle = self._open(settings)

    def _open(self, settings: Settings) -> int:
        err = ctypes.c_void_p()
        handle = self._lib.gascoigne_open(settings.to_json().encode(), ctypes.byref(err))
        if not handle:
            raise NativeError(self._take(err.value) or "open failed")
        return int(handle)

    def _take(self, ptr: int | None) -> str:
        """Copy and release a string the library returned."""
        if not ptr:
            return ""
        try:
            return ctypes.string_at(ptr).decode()
        finally:
            self._lib.gascoigne_free(ptr)

    def _call(self, fn: str, *args: bytes) -> str:
        err = ctypes.c_void_p()
        out = getattr(self._lib, fn)(self._handle, *args, ctypes.byref(err))
        if not out:
            raise NativeError(self._take(err.value) or f"{fn} failed")
        return self._take(out)

    def optimize(self, request: OptimizeRequest) -> Result:
        body = json.dumps(request.to_json()).encode()
        return Result.from_json(json.loads(self._call("gascoigne_optimize", body)))

    def raw(self, raw_id: str) -> str:
        return self._call("gascoigne_raw", raw_id.encode())

    def totals(self, query: dict[str, str]) -> list[Total]:
        return [Total.from_json(d) for d in json.loads(self._call("gascoigne_stats", _doc(query)))]

    def runs(self, query: dict[str, str | int]) -> list[Run]:
        return [Run.from_json(d) for d in json.loads(self._call("gascoigne_recent", _doc(query)))]

    def close(self) -> None:
        with self._lock:
            handle, self._handle = self._handle, 0
        if handle:
            self._lib.gascoigne_close(handle)


def _doc(query: dict[str, str] | dict[str, str | int]) -> bytes:
    return json.dumps(query).encode()


def _bind(lib: ctypes.CDLL) -> ctypes.CDLL:
    # Returned strings are taken as raw pointers so they can be released with gascoigne_free.
    err = ctypes.POINTER(ctypes.c_void_p)
    lib.gascoigne_abi_version.restype = ctypes.c_int
    lib.gascoigne_open.argtypes = [ctypes.c_char_p, err]
    lib.gascoigne_open.restype = ctypes.c_uint64
    for fn in (
        "gascoigne_optimize",
        "gascoigne_raw",
        "gascoigne_stats",
        "gascoigne_recent",
    ):
        getattr(lib, fn).argtypes = [ctypes.c_uint64, ctypes.c_char_p, err]
        getattr(lib, fn).restype = ctypes.c_void_p
    lib.gascoigne_close.argtypes = [ctypes.c_uint64]
    lib.gascoigne_free.argtypes = [ctypes.c_void_p]
    return lib
