#!/usr/bin/env python3
"""Fills the native packages of every SDK with gzip-compressed copies of libgascoigne.

Usage: scripts/bundle_native.py [DIR] [--platform <os>-<arch>]

DIR holds one folder per platform, `<os>-<arch>/<library file>` (os: linux, darwin, windows;
arch: amd64, arm64), as the release archives unpack. `--platform` keeps just that one, which is
how scripts/package_native.py builds a package per platform. Without DIR the library built by
`mise run native:build` is bundled for the current platform only. Each package gets the same
layout, `<os>-<arch>/<library file>.gz`; see spec/native.md.
"""

import gzip
import platform
import shutil
import sys
from pathlib import Path

LIBS = ("libgascoigne.so", "libgascoigne.dylib", "gascoigne.dll")

# Where each language's native package keeps the bundle (all git-ignored).
TARGETS = (
    "python/gascoigne-native/src/gascoigne_native/lib",
    "typescript/native-template/lib",
    "java/native/src/main/resources/gascoigne/native",
    "dotnet/src/Gascoigne.Native/lib",
    "rust/native/lib",
)


def host() -> str:
    system = {"Linux": "linux", "Darwin": "darwin", "Windows": "windows"}[platform.system()]
    arch = {"x86_64": "amd64", "AMD64": "amd64", "arm64": "arm64", "aarch64": "arm64"}[
        platform.machine()
    ]
    return f"{system}-{arch}"


def platforms(source: Path | None) -> dict[str, Path]:
    if source is None:
        built = [p for p in (Path("native/dist") / n for n in LIBS) if p.is_file()]
        if not built:
            sys.exit("no native/dist library: run `mise run native:build` or pass DIR")
        return {host(): built[0]}
    found = {d.name: f for d in sorted(source.iterdir()) for f in d.iterdir() if f.name in LIBS}
    if not found:
        sys.exit(f"{source}: no <os>-<arch>/<library> files")
    return found


def main() -> int:
    args = sys.argv[1:]
    only = args.pop(args.index("--platform") + 1) if "--platform" in args else None
    args = [a for a in args if a != "--platform"]
    source = Path(args[0]) if args else None
    libs = platforms(source)
    if only:
        libs = {only: libs[only]}
    for target in map(Path, TARGETS):
        shutil.rmtree(target, ignore_errors=True)
        for name, lib in libs.items():
            out = target / name / (lib.name + ".gz")
            out.parent.mkdir(parents=True)
            with lib.open("rb") as src, gzip.GzipFile(out, "wb", 9, mtime=0) as dst:
                shutil.copyfileobj(src, dst)
        print(f"{target}: {', '.join(libs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
