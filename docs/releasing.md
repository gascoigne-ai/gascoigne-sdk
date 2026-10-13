# Releasing

Each ecosystem has its own version and tag prefix; pushing the tag runs `.github/workflows/release.yml`.

| Ecosystem | Tag | Registry | Credentials (GitHub environment) |
|---|---|---|---|
| Python | `py-v0.1.0` | PyPI | trusted publishing (OIDC) for this repo, workflow `release.yml`, environment `pypi` |
| TypeScript | `ts-v0.1.0` | npm | `NPM_TOKEN` in environment `npm` |
| Go | `go/v0.1.0` | Go proxy | none (the tag is the release) |
| Java | `java-v0.1.0` | Maven Central | OSSRH token + GPG key in `maven-central` (workflow only builds the jar until set up) |
| .NET | `dotnet-v0.1.0` | NuGet | `NUGET_API_KEY` in environment `nuget` |
| Rust | `rust-v0.1.0` | crates.io | `CARGO_REGISTRY_TOKEN` in environment `crates-io` |

Bump the version in the package file (`pyproject.toml`, `package.json`, `pom.xml`, `*.csproj`, `Cargo.toml`)
in the commit before tagging. Every release runs the language's `mise run <lang>:check` first.
