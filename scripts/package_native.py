#!/usr/bin/env python3
"""Builds the native packages of every SDK, one per platform, so an application downloads one
library (about 9 MB) instead of all of them (about 48 MB). See spec/native.md.

Usage: scripts/package_native.py DIR OUT

DIR holds `<os>-<arch>/<library file>` folders (release archives, unpacked); OUT receives:

- Python: one wheel per platform for `gascoigne-native`, tagged for that platform, so pip picks.
- npm: `@gascoigne-ai/sdk-native-<os>-<cpu>` per platform, and `@gascoigne-ai/sdk-native`, which
  lists them as optional dependencies so npm installs only the one that fits `os` and `cpu`.
- Java: one `gascoigne-native-<version>-<os>-<arch>.jar` per platform, to attach as a classifier
  of the pom-only `ai.gascoigne:gascoigne-native`.
- .NET: `Gascoigne.Native.<rid>` per platform; applications reference their system's one.
- Rust: `gascoigne-native-<os>-<arch>` crates, and `gascoigne-native`, which depends on the one for
  the target (`cfg(target_os, target_arch)`). Publish the `gascoigne` crate first.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Platform:
    key: str
    py_tag: str
    npm_os: str
    npm_cpu: str
    rid: str
    rust_os: str
    rust_arch: str


PLATFORMS = [
    Platform(
        "linux-amd64", "manylinux_2_17_x86_64", "linux", "x64", "linux-x64", "linux", "x86_64"
    ),
    Platform(
        "linux-arm64", "manylinux_2_17_aarch64", "linux", "arm64", "linux-arm64", "linux", "aarch64"
    ),
    Platform("darwin-amd64", "macosx_11_0_x86_64", "darwin", "x64", "osx-x64", "macos", "x86_64"),
    Platform(
        "darwin-arm64", "macosx_11_0_arm64", "darwin", "arm64", "osx-arm64", "macos", "aarch64"
    ),
    Platform("windows-amd64", "win_amd64", "win32", "x64", "win-x64", "windows", "x86_64"),
]


def run(*cmd: str, cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def bundle(source: Path, p: Platform) -> None:
    run(sys.executable, "scripts/bundle_native.py", str(source), "--platform", p.key)


def version(path: str, pattern: str) -> str:
    match = re.search(pattern, Path(path).read_text())
    assert match, path
    return match.group(1)


def python(p: Platform, out: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        run("uv", "build", "--wheel", "--out-dir", tmp, cwd=Path("python/gascoigne-native"))
        wheel = next(Path(tmp).glob("*.whl"))
        run("uvx", "wheel", "tags", "--python-tag", "py3", "--abi-tag", "none",
            "--platform-tag", p.py_tag, "--remove", str(wheel))
        for tagged in Path(tmp).glob("*.whl"):
            shutil.move(tagged, out / tagged.name)


def npm(p: Platform, out: Path, ver: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "pkg"
        shutil.copytree("typescript/native-template", pkg)
        manifest = {
            "name": f"@gascoigne-ai/sdk-native-{p.npm_os}-{p.npm_cpu}",
            "version": ver,
            "description": f"libgascoigne for {p.key}, for @gascoigne-ai/sdk native mode",
            "license": "Apache-2.0",
            "os": [p.npm_os],
            "cpu": [p.npm_cpu],
            "files": ["lib", "README.md"],
            "repository": "github:gascoigne-ai/gascoigne-sdk",
            "publishConfig": {"access": "public"},
        }
        (pkg / "package.json").write_text(json.dumps(manifest, indent=2) + "\n")
        run("npm", "pack", "--pack-destination", str(out), cwd=pkg)


def npm_meta(out: Path, ver: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "pkg"
        pkg.mkdir()
        shutil.copy("typescript/native-template/README.md", pkg)
        manifest = {
            "name": "@gascoigne-ai/sdk-native",
            "version": ver,
            "description": "The gascoigne engine as a native library, for @gascoigne-ai/sdk",
            "license": "Apache-2.0",
            "files": ["README.md"],
            "optionalDependencies": {
                f"@gascoigne-ai/sdk-native-{p.npm_os}-{p.npm_cpu}": ver for p in PLATFORMS
            },
            "repository": "github:gascoigne-ai/gascoigne-sdk",
            "publishConfig": {"access": "public"},
        }
        (pkg / "package.json").write_text(json.dumps(manifest, indent=2) + "\n")
        run("npm", "pack", "--pack-destination", str(out), cwd=pkg)


def java(p: Platform, out: Path, ver: str) -> None:
    root = Path("java/native/src/main/resources")
    jar = out / f"gascoigne-native-{ver}-{p.key}.jar"
    with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
        for f in sorted((root / "gascoigne/native" / p.key).glob("*.gz")):
            z.write(f, f.relative_to(root).as_posix())


def dotnet(p: Platform, out: Path) -> None:
    run("dotnet", "pack", "dotnet/src/Gascoigne.Native", "-c", "Release", f"-p:Rid={p.rid}",
        "-o", str(out))


RUST_VARIANT = """[package]
name = "gascoigne-native-{key}"
version = "{ver}"
edition = "2021"
description = "libgascoigne for {key}, for the gascoigne crate's native mode"
license = "Apache-2.0"
repository = "https://github.com/gascoigne-ai/gascoigne-sdk"
readme = "README.md"

[dependencies]
flate2 = "1"
gascoigne = {{ version = "{core}", features = ["native"] }}
sha2 = "0.10"

[workspace]
"""

RUST_META = """[package]
name = "gascoigne-native"
version = "{ver}"
edition = "2021"
description = "The gascoigne engine as a native library, for the gascoigne crate"
license = "Apache-2.0"
repository = "https://github.com/gascoigne-ai/gascoigne-sdk"
readme = "README.md"

{targets}
[workspace]
"""


def rust(p: Platform, out: Path, ver: str, core: str) -> None:
    name = f"gascoigne-native-{p.key}"
    crate = out / name
    skip = shutil.ignore_patterns("target", "tests", "Cargo.*")
    shutil.copytree("rust/native", crate, ignore=skip)
    shutil.copy("rust/native/build.rs", crate / "build.rs")
    (crate / "Cargo.toml").write_text(RUST_VARIANT.format(key=p.key, ver=ver, core=core))
    crate_file(crate, out)


def crate_file(crate: Path, out: Path) -> None:
    """Packages a generated crate and leaves the .crate in `out`. Needs the `gascoigne` crate of
    the version in rust/Cargo.toml on the registry, because the crates depend on it."""
    run("cargo", "package", "--allow-dirty", "--manifest-path", str(crate / "Cargo.toml"))
    for packaged in (crate / "target/package").glob("*.crate"):
        shutil.move(packaged, out / packaged.name)
    shutil.rmtree(crate)


def rust_meta(out: Path, ver: str) -> None:
    targets, reexports = [], []
    for p in PLATFORMS:
        cond = f'cfg(all(target_os = "{p.rust_os}", target_arch = "{p.rust_arch}"))'
        targets.append(
            f"[target.'{cond}'.dependencies]\ngascoigne-native-{p.key} = \"{ver}\"\n"
        )
        crate = f"gascoigne_native_{p.key.replace('-', '_')}"
        cfg = f'#[cfg(all(target_os = "{p.rust_os}", target_arch = "{p.rust_arch}"))]'
        reexports.append(f"{cfg}\npub use {crate}::*;\n")
    crate = out / "gascoigne-native"
    (crate / "src").mkdir(parents=True)
    shutil.copy("rust/native/README.md", crate)
    (crate / "Cargo.toml").write_text(RUST_META.format(ver=ver, targets="\n".join(targets)))
    (crate / "src/lib.rs").write_text(
        "//! The native variant of the `gascoigne` crate: re-exports the crate that carries the\n"
        "//! library for the target platform (see spec/native.md).\n\n" + "\n".join(reexports)
    )
    crate_file(crate, out)


def main() -> int:
    source, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    ver = Path("native/VERSION").read_text().strip()
    core = version("rust/Cargo.toml", r'(?m)^version = "([^"]+)"')
    present = {d.name for d in source.iterdir() if d.is_dir()}
    for p in PLATFORMS:
        if p.key not in present:
            print(f"skip {p.key}: not in {source}")
            continue
        bundle(source, p)
        python(p, out)
        npm(p, out, ver)
        java(p, out, ver)
        dotnet(p, out)
        rust(p, out, ver, core)
    npm_meta(out, ver)
    rust_meta(out, ver)
    print(f"packages in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
