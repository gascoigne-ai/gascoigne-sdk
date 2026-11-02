"""Embedded mode, against the real shared library built from native/ (skipped when absent)."""

from pathlib import Path

import pytest
from gascoigne.native import NativeError, Settings, _names, find_library
from gascoigne.runtime import Runtime

LIB = Path(__file__).parents[3] / "native" / "dist" / "libgascoigne.so"


def test_native_without_library_raises_and_names_where_it_looked(monkeypatch):
    monkeypatch.setenv("GASCOIGNE_LIB", "/nonexistent/libgascoigne.so")
    with pytest.raises(NativeError, match=r"libgascoigne not found.*GASCOIGNE_LIB"):
        Runtime(mode="native")


def test_system_directories_are_searched(monkeypatch, tmp_path):
    monkeypatch.delenv("GASCOIGNE_LIB", raising=False)
    monkeypatch.setenv("GASCOIGNE_UNPACK", "off")
    monkeypatch.setenv("GASCOIGNE_LIB_PATH", str(tmp_path))
    assert find_library()[0] is None
    lib = tmp_path / _names()[0]
    lib.write_bytes(b"x")
    assert find_library()[0] == lib


@pytest.mark.skipif(not LIB.exists(), reason="build native/ first: mise run native:check")
def test_embedded_optimizes_and_returns_original(monkeypatch, tmp_path):
    monkeypatch.setenv("GASCOIGNE_LIB", str(LIB))
    for var in ("GASCOIGNE_SDK", "GASCOIGNE_SERVER"):
        monkeypatch.delenv(var, raising=False)
    db = tmp_path / "ledger.db"
    settings = Settings(config=f"extensions:\n  ledger:\n    path: {db}\n", ignore_user_file=True)
    rt = Runtime(mode="native", settings=settings)
    raw = "INFO request served path=/api/items status=200 ms=12\n" * 400
    res = rt.optimize_result(raw, tool="bash", cmd="tail app.log")
    assert res.out_tokens < res.raw_tokens and res.raw_id
    assert rt.raw(res.raw_id) == raw
    assert rt.proxy_base_url() is None
    rt.close()


def test_unpack_is_idempotent_and_checks_content(monkeypatch, tmp_path):
    import gzip

    from gascoigne.native import unpack

    monkeypatch.setenv("GASCOIGNE_LIB_DIR", str(tmp_path / "out"))
    bundled = tmp_path / "libgascoigne.so.gz"
    bundled.write_bytes(gzip.compress(b"library bytes"))
    first = unpack(bundled)
    assert first.read_bytes() == b"library bytes"
    assert first.parent.name.startswith("gascoigne-native-")
    assert unpack(bundled) == first
    # A file replaced behind our back is rewritten, never loaded as is.
    first.write_bytes(b"tampered")
    assert unpack(bundled).read_bytes() == b"library bytes"


@pytest.mark.skipif(not LIB.exists(), reason="build native/ first: mise run native:build")
def test_bundle_is_found_and_unpacked_to_tmp(monkeypatch, tmp_path):
    import gascoigne_native

    if not (gascoigne_native.LIB_DIR).exists():
        pytest.skip("run scripts/bundle_native.py")
    monkeypatch.delenv("GASCOIGNE_LIB", raising=False)
    monkeypatch.setenv("GASCOIGNE_LIB_DIR", str(tmp_path))
    monkeypatch.setenv("GASCOIGNE_LIB_PATH", str(tmp_path / "none"))
    path = find_library()[0]
    assert path is not None and tmp_path in path.parents
    # The unpacked copy loads and optimizes, with no GASCOIGNE_LIB involved.
    db = tmp_path / "ledger.db"
    settings = Settings(config=f"extensions:\n  ledger:\n    path: {db}\n", ignore_user_file=True)
    rt = Runtime(mode="native", settings=settings)
    raw = "INFO request served path=/api/items status=200 ms=12\n" * 400
    assert rt.optimize_result(raw).raw_id
    rt.close()
    monkeypatch.setenv("GASCOIGNE_UNPACK", "off")
    assert find_library()[0] is None
