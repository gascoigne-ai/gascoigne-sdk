# Releasing

Since 0.9.0 every ecosystem and the native library carry the version of the CLI release (`gascoigne-cli`
`internal/version`); each keeps its own tag prefix. Pushing the tag runs
`.github/workflows/release.yml`.

| Ecosystem | Tag | Artifacts on the GitHub release |
|---|---|---|
| Python | `py-v0.11.0` | wheel, sdist, `checksums.txt` |
| TypeScript | `ts-v0.11.0` | one `.tgz` per package (`@gascoigne-ai/sdk`, `@gascoigne-ai/ai-sdk`) |
| Go | `go/v0.11.0` | a signed source archive; the Go module proxy serves the tag itself |
| Java | `java-v0.11.0` | `gascoigne` and `gascoigne-spring-ai` jars |
| .NET | `dotnet-v0.11.0` | `Gascoigne` and `Gascoigne.Extensions.AI` `.nupkg` |
| Rust | `rust-v0.11.0` | the `.crate` |
| Native library | `native-v0.11.0` | `libgascoigne-<version>-<os>-<arch>.tar.gz` per platform, and the per-platform packages of every language |

The native release builds the library on every platform, attaches it, and builds the per-platform
packages of every language with `scripts/package_native.py` (a wheel, an npm package, a Java
classifier jar, a NuGet package and a crate per platform, plus the npm and Rust meta packages that
pick the right one). Publish the `gascoigne` crate before tagging `native-v*`, because the Rust
native crates depend on it; until it is on crates.io the packager skips the Rust crates and ships the rest. Language tags do not bundle anything.

## Steps

1. Set the version in the package files: `pyproject.toml`, the two `package.json`, the two
   `pom.xml`, the two `.csproj`, `Cargo.toml`, `native/VERSION`. Go has no version file.
2. Commit it, for example `release: python 0.2.0 <headline>`, and push.
3. `git tag py-v0.2.0 && git push origin py-v0.2.0`.

The workflow checks that the tag matches the files (`scripts/check_version.py`), runs the language's
`mise run <lang>:check`, builds the artifacts, writes `checksums.txt`, signs everything (build
provenance and a cosign signature, see [`verifying.md`](verifying.md)) and creates the GitHub release
with generated notes. None of this needs a secret.

## GitHub Packages

npm, Maven and NuGet releases are also published to GitHub Packages automatically (no setup, the
workflow token is enough). How to install them: [`github-packages.md`](github-packages.md).

## Publishing to a public registry

A second job per ecosystem publishes the release's artifacts. It runs only when the repository
variable is `true` and the credentials exist:

| Variable | Registry | Credentials |
|---|---|---|
| `PUBLISH_PYPI` | PyPI | trusted publishing for this repo, workflow `release.yml`, environment `pypi` |
| `PUBLISH_NPM` | npm | `NPM_TOKEN` secret in environment `npm` |
| `PUBLISH_NUGET` | NuGet | `NUGET_API_KEY` secret in environment `nuget` |
| `PUBLISH_CRATES` | crates.io | `CARGO_REGISTRY_TOKEN` secret in environment `crates-io` |
| `PUBLISH_MAVEN` | Maven Central | namespace, central-publishing plugin and GPG key (not set up yet) |

Set a variable with `gh variable set PUBLISH_PYPI --body true`.
