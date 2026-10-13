#!/usr/bin/env python3
"""Fails when a release tag does not match the version in the package files.

Usage: scripts/check_version.py <ecosystem> <version>
Ecosystems: py ts go java dotnet rust. Go has no version file: the tag is the version.
"""

import json
import re
import sys
import tomllib
from pathlib import Path


def python() -> list[str]:
    project = tomllib.loads(Path("python/gascoigne/pyproject.toml").read_text())["project"]
    return [project["version"]]


def typescript() -> list[str]:
    packages = ("sdk", "ai-sdk")
    return [
        json.loads(Path(f"typescript/packages/{p}/package.json").read_text())["version"]
        for p in packages
    ]


def java() -> list[str]:
    pattern = re.compile(r"<artifactId>gascoigne(?:-spring-ai)?</artifactId>\s*<version>([^<]+)")
    poms = ("java/pom.xml", "java/spring-ai/pom.xml")
    return [pattern.search(Path(p).read_text()).group(1) for p in poms]


def dotnet() -> list[str]:
    pattern = re.compile(r"<Version>([^<]+)</Version>")
    projects = ("Gascoigne", "Gascoigne.Extensions.AI")
    return [
        pattern.search(Path(f"dotnet/src/{p}/{p}.csproj").read_text()).group(1) for p in projects
    ]


def rust() -> list[str]:
    return [tomllib.loads(Path("rust/Cargo.toml").read_text())["package"]["version"]]


VERSIONS = {"py": python, "ts": typescript, "java": java, "dotnet": dotnet, "rust": rust}


def main() -> int:
    ecosystem, version = sys.argv[1], sys.argv[2]
    found = VERSIONS[ecosystem]() if ecosystem in VERSIONS else [version]
    if any(v != version for v in found):
        print(f"tag says {version} but the package files say {found}")
        return 1
    print(f"{ecosystem} {version} matches the package files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
