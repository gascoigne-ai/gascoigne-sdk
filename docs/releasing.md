# Releasing

Each ecosystem has its own version and tag prefix. Pushing the tag runs
`.github/workflows/release.yml`.

| Ecosystem | Tag | Artifacts on the GitHub release |
|---|---|---|
| Python | `py-v0.1.0` | wheel, sdist, `checksums.txt` |
| TypeScript | `ts-v0.1.0` | one `.tgz` per package (`@gascoigne-ai/sdk`, `@gascoigne-ai/ai-sdk`) |
| Go | `go/v0.1.0` | none; the Go module proxy serves the tag |
| Java | `java-v0.1.0` | `gascoigne` and `gascoigne-spring-ai` jars |
| .NET | `dotnet-v0.1.0` | `Gascoigne` and `Gascoigne.Extensions.AI` `.nupkg` |
| Rust | `rust-v0.1.0` | the `.crate` |

## Steps

1. Set the version in the package files: `pyproject.toml`, the two `package.json`, the two
   `pom.xml`, the two `.csproj`, `Cargo.toml`. Go has no version file.
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
