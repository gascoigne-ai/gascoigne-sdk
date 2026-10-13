# Install and use

Every SDK needs the `gascoigne` CLI on `PATH` (without it the SDK warns once and passes text
through unchanged):

```sh
mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne
```

The SDKs are not on PyPI, npmjs, crates.io or Maven Central yet. Install them from GitHub:

| Language | Where it lives | Version tags |
|---|---|---|
| Python | release assets, or the git repo | `py-v0.1.0` |
| TypeScript | GitHub Packages (npm), or release tarballs | `ts-v0.1.1` |
| Go | the git repo (Go modules) | `go/v0.1.0`, used as `v0.1.0` |
| Java | GitHub Packages (Maven), or release jars | `java-v0.1.1` |
| .NET | GitHub Packages (NuGet), or release `.nupkg` | `dotnet-v0.1.1` |
| Rust | the git repo | `rust-v0.1.0` |

**Access.** While the repository is private, every command below needs credentials: sign in with
`gh auth login` (and `gh auth setup-git` so git uses it), or use a personal access token (classic)
with `repo` and, for GitHub Packages, `read:packages`. Once the repository is public, the git and
release-asset installs work without any. GitHub Packages asks for a token either way.

## Python

```sh
# from a release (gh uses your login)
gh release download py-v0.1.0 -R gascoigne-ai/gascoigne-sdk -p '*.whl'
uv add ./gascoigne-0.1.0-py3-none-any.whl

# or straight from git
uv add "gascoigne @ git+https://github.com/gascoigne-ai/gascoigne-sdk@py-v0.1.0#subdirectory=python/gascoigne"
```

```python
import gascoigne

gascoigne.init(agent="my-app")
search = gascoigne.wrap_tool(search)      # any tool function returning str
# or: gascoigne.auto()                    # opt in to MCP and LangChain tools
```

## TypeScript

```sh
# GitHub Packages: see github-packages.md for the .npmrc
npm install @gascoigne-ai/sdk @gascoigne-ai/ai-sdk

# or a release tarball
gh release download ts-v0.1.1 -R gascoigne-ai/gascoigne-sdk -p '*.tgz'
npm install ./gascoigne-ai-sdk-0.1.1.tgz
```

```ts
import { init, wrapTool } from "@gascoigne-ai/sdk";
import { wrapTools } from "@gascoigne-ai/ai-sdk";   // Vercel AI SDK tools

init({ agent: "my-app" });
const search = wrapTool(searchFn, "search");
```

## Go

```sh
export GOPRIVATE=github.com/gascoigne-ai/*      # only while the repository is private
go get github.com/gascoigne-ai/gascoigne-sdk/go@v0.1.0
```

```go
import "github.com/gascoigne-ai/gascoigne-sdk/go/gascoigne"

rt := gascoigne.New(gascoigne.Options{Agent: "my-app"})
logs := rt.WrapTool(searchTool)       // any value with Name, Description and Call
```

## Java

GitHub Packages (Maven), configured as in [`github-packages.md`](github-packages.md):

```xml
<dependency>
  <groupId>ai.gascoigne</groupId>
  <artifactId>gascoigne</artifactId>
  <version>0.1.1</version>
</dependency>
<!-- Spring AI: one annotation decorates every tool call -->
<dependency>
  <groupId>ai.gascoigne</groupId>
  <artifactId>gascoigne-spring-ai</artifactId>
  <version>0.1.1</version>
</dependency>
```

```java
Gascoigne gascoigne = Gascoigne.builder().agent("my-app").build();
String shortText = gascoigne.optimize(toolOutput, Attrs.tool("search"));
// Spring AI: @EnableGascoigne on your application class
```

## .NET

NuGet from GitHub Packages, configured as in [`github-packages.md`](github-packages.md):

```sh
dotnet add package Gascoigne
dotnet add package Gascoigne.Extensions.AI     # Microsoft.Extensions.AI middleware
```

```csharp
using var gascoigne = new GascoigneClient(new GascoigneOptions { Agent = "my-app" });
string shortText = await gascoigne.OptimizeAsync(toolOutput, new Attrs { Tool = "search" });
// Microsoft.Extensions.AI: .UseFunctionInvocation(configure: c => c.UseGascoigne(gascoigne))
```

## Rust

```sh
cargo add gascoigne --git https://github.com/gascoigne-ai/gascoigne-sdk --tag rust-v0.1.0
# while the repository is private: CARGO_NET_GIT_FETCH_WITH_CLI=true so cargo uses git's login
```

```rust
let rt = gascoigne::Runtime::new("my-app");
let short = rt.optimize(&tool_output, &gascoigne::Attrs::tool("search"));
```

## Check that it works

Run a demo (`demos/README.md`), or call `optimize` on a long log. With the CLI missing you will see
one warning, `gascoigne-cli not found on PATH`, and the text comes back unchanged.
