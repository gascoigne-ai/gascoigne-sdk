# Changelog

All notable changes to the gascoigne SDKs. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow the CLI release (from 0.9.0); each ecosystem has its own tag prefix
(`py-v`, `ts-v`, `go/v`, `java-v`, `dotnet-v`, `rust-v`, `native-v`, see `docs/releasing.md`); entries name the
SDKs they touch.

## [Unreleased]

## [0.9.0] - 2026-11-02

Native mode: every SDK can run the engine inside the application process instead of talking to a `gascoigne`
server. It needs `gascoigne-cli` 0.9.0 or later (the `inproc` facade). Every SDK and the native library move to 0.9.0
to match the CLI release they were built against (see Versioning).

### Added

- `native/`: `libgascoigne`, a C ABI library (`go build -buildmode=c-shared`) that runs the engine in the process,
  with no server, HTTP or `gascoigne` binary. `native-v*` tags build it for linux, macOS and Windows (amd64, arm64).
  Contract in `spec/native.md`.
- Python, TypeScript, Go, Java, .NET and Rust: native mode loads `libgascoigne` (ctypes, koffi, in-process Go
  `Backend`, JNA, run-time loading, libloading). `GASCOIGNE_MODE=native|proxy` picks the default, the argument to
  `init` wins; `GASCOIGNE_LIB`, `GASCOIGNE_LIB_PATH` and `GASCOIGNE_BIN` locate the library.
- Native mode demos in every language.

### Changed

- Docs describe a native and a proxy variant of every SDK. Proxy mode is unchanged.
- Commit style check allows `chore` commits.

### Versioning

- From 0.9.0 every package (Python, TypeScript, Go, Java, .NET, Rust and `native`) carries the CLI's version number.
  Earlier versions were independent (0.1.x).

## 2026-10-14 - signed releases

### Release

- Python 0.1.1 (first signed release); TypeScript, Java and .NET 0.1.2; Rust 0.1.1; Go 0.1.1.
- Release files are signed with build provenance and cosign (`docs/verifying.md`), attached with checksums to a
  GitHub release; npm, Maven and NuGet packages also go to GitHub Packages. The Go release carries a signed source
  archive.

### Changed

- TypeScript publishes under the `@gascoigne-ai` scope.
- Dependencies: vitest 4.1.11 (path traversal fix), golang.org/x/crypto 0.52.0 in the demos, jackson-databind
  2.22.3, maven-compiler-plugin 3.16.0.
- The repository is public: install without a login (`docs/install.md`).
- Removed the CrewAI and LlamaIndex demos.

### Fixed

- npm publish takes the tarball as a path; e2e runs the pytest suite only and waits for the CLI API.
- Demos use random request ids so the proxy cache cannot hide results.

## 0.1.0 - 2026-10-13 to 2026-10-14 - first SDKs

### Added

- Python: core, `wrap_tool`, `auto()` for MCP and LangChain tools, demos for nine frameworks.
- TypeScript: core and Vercel AI SDK helper.
- Go, Java (Spring AI `@EnableGascoigne`, LangChain4j), .NET (`UseGascoigne` for Microsoft.Extensions.AI) and
  Rust SDKs, with typed wire models, linters, CI and release workflows.
- Protocol spec in `spec/protocol.md`; one demos tree for all languages, with proxy-mode demos.
