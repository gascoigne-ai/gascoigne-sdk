# Changelog

All notable changes to the gascoigne SDKs. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Since 0.9.0 every SDK and the native library carry the
version of the CLI release they were built with. Each ecosystem has its own tag prefix (`py-v`, `ts-v`, `go/v`,
`java-v`, `dotnet-v`, `rust-v`, `native-v`, see `docs/releasing.md`). Each release starts with "In short": what
changed for you, in plain words.

## [Unreleased]

### In short

- **Read your savings from your app.** Every SDK has `totals`, `runs` and `costs`: tokens saved per agent, model,
  day or session, the recent runs with the id of each original, and what the saved tokens are worth.
- **A ledger that lives in memory.** `ledger: memory` keeps the record in your process: no file, nothing left
  behind. The default stays the sqlite file the CLI and its dashboard share.
- **Your prices, or no dollars.** `pricing` sets prices per model, or `billing: subscription` for a flat plan, where
  no dollar figure is shown. Needs `gascoigne-cli` with the same release in proxy mode.

### Added

- `gascoigne_stats`, `gascoigne_recent`, `gascoigne_costs` in the native library, and `GET /sdk/v1/stats`,
  `/recent`, `/costs` in the protocol. Native ABI is now 2: an SDK and a library of different ABIs refuse each other.
- Options `ledger` (`file` or `memory`) and `pricing` (`billing`, `prices`, `file`) for the embedded engine.
- `totals`, `runs`, `costs` in the Go, Python, TypeScript, Java, .NET and Rust SDKs. They never raise and never
  open the optimize breaker; on any failure they return nothing.

## [0.9.1] - 2026-11-02

The first release of the 0.9 line that shipped: native mode in every SDK, native demos for every framework, and a
README you can try in a minute. It needs `gascoigne-cli` 0.9.1 or later in proxy mode.

### In short

- **Run gascoigne inside your app.** Every SDK can load `libgascoigne` and shorten tool results in your own process:
  no server, no `gascoigne` binary, one less thing to deploy.
- **More demos you can run.** Native demos for every Python and TypeScript framework and for Spring AI, next to the
  wrap, proxy and auto ones. `GASCOIGNE_DEMO_DRY=1` runs them without an API key.
- **A README that starts with a try-it.** A real before and after (12,425 to 145 tokens), a two-line start per
  language, and native or proxy side by side.
- **Releases that build.** The release workflow now fetches the CLI it needs, the .NET package builds on net8.0 again,
  and the macOS Intel library builds on a current runner.

### Added

- Native demos for the Python (agno, google-adk, langchain, openai-agents, pydantic-ai, smolagents), TypeScript
  (langchain, mastra, openai-agents) and Spring AI demos.

### Changed

- README: a 30 second try-it, a real before and after, and native or proxy in one table.
- Install, release and verifying guides name the 0.9.1 tags.

### Fixed

- Release jobs check out the CLI that `native:build` needs.
- .NET: the digest of the unpacked library no longer uses an API that exists only on .NET 9, so the net8.0 target
  compiles. `dotnet:check` builds net8.0 too.
- The darwin-amd64 library builds on `macos-15-intel`, because `macos-13` is retired.

## [0.9.0] - 2026-11-02

Native mode and the native library. The 0.9.0 tags did not start the release workflow (more than three tags in one
push), so 0.9.1 is the first release of this line.

### In short

- **Run gascoigne inside your app (native mode).** Python, TypeScript, Go, Java, .NET and Rust load `libgascoigne` and
  do the work in your process. Simpler to deploy and quicker per call. The old way, through the local server, still
  works and stays the default.
- **One version number.** The SDKs now share the CLI's version.

### Added

- `native/`: `libgascoigne`, a C ABI library (`go build -buildmode=c-shared`) that runs the engine in the process,
  built for Linux, macOS and Windows (amd64, arm64) by `native-v*` tags. Contract in `spec/native.md`.
- Native mode in every SDK (ctypes, koffi, in-process Go `Backend`, JNA, run-time loading, libloading).
  `GASCOIGNE_MODE=native|proxy` picks the default; the argument to `init` wins; `GASCOIGNE_LIB`,
  `GASCOIGNE_LIB_PATH` and `GASCOIGNE_BIN` locate the library.
- Native demos in every language.

### Changed

- Docs describe a native and a proxy variant of every SDK. Proxy mode is unchanged.
- Commit style check allows `chore` commits.

## 2026-10-14 - signed releases

### In short

- **Releases you can verify.** Release files are signed with build provenance and cosign (`docs/verifying.md`), and
  come with checksums.
- **Easy installs.** npm, Maven and NuGet packages are on GitHub Packages, and the repository is public, so you
  install without a login.
- **Versions:** Python 0.1.1, TypeScript, Java and .NET 0.1.2, Rust 0.1.1, Go 0.1.1.

### Changed

- TypeScript publishes under the `@gascoigne-ai` scope.
- Dependencies: vitest 4.1.11 (path traversal fix), golang.org/x/crypto 0.52.0 in the demos, jackson-databind
  2.22.3, maven-compiler-plugin 3.16.0.
- Removed the CrewAI and LlamaIndex demos.

### Fixed

- npm publish takes the tarball as a path; e2e runs the pytest suite only and waits for the CLI API.
- Demos use random request ids so the proxy cache cannot hide results.

## 0.1.0 - 2026-10-13 to 2026-10-14 - first SDKs

### In short

- **Shorter tool results in your agent app,** in six languages: Python, TypeScript, Go, Java, .NET and Rust, with
  one surface: `optimize`, `raw`, `proxy_base_url`, `stats`, `wrap_tool`.
- **Framework demos** to copy from, including proxy mode, and an `auto()` call that decorates MCP and LangChain tools
  when you ask for it.

### Added

- Python: core, `wrap_tool`, `auto()` for MCP and LangChain tools, demos for nine frameworks.
- TypeScript: core and Vercel AI SDK helper.
- Go, Java (Spring AI `@EnableGascoigne`, LangChain4j), .NET (`UseGascoigne` for Microsoft.Extensions.AI) and
  Rust SDKs, with typed wire models, linters, CI and release workflows.
- Protocol spec in `spec/protocol.md`; one demos tree for all languages, with proxy-mode demos.
