# Install and use

Every SDK needs the `gascoigne` CLI on `PATH` (without it the SDK warns once and passes text
through unchanged):

```sh
mise use -g go:github.com/gascoigne-ai/gascoigne-cli/cmd/gascoigne
```

The SDKs are not on PyPI, npmjs, crates.io or Maven Central yet. Install them from GitHub:

| Language | Where it lives | Version tag |
|---|---|---|
| Python | release wheel, or the git repo | `py-v0.1.0` |
| TypeScript | release tarballs, or GitHub Packages (npm) | `ts-v0.1.1` |
| Go | the git repo (Go modules) | `go/v0.1.0`, used as `v0.1.0` |
| Java | GitHub Packages (Maven) | `java-v0.1.1` |
| .NET | release `.nupkg`, or GitHub Packages (NuGet) | `dotnet-v0.1.1` |
| Rust | the git repo | `rust-v0.1.0` |

The repository and its releases are public, so the git and release-file installs need no login.
GitHub Packages is the exception: it asks for a token even for public packages
([`github-packages.md`](github-packages.md)).

## Python

```sh
uv add https://github.com/gascoigne-ai/gascoigne-sdk/releases/download/py-v0.1.0/gascoigne-0.1.0-py3-none-any.whl

# or straight from git
uv add "gascoigne @ git+https://github.com/gascoigne-ai/gascoigne-sdk@py-v0.1.0#subdirectory=python/gascoigne"
```

With pip: `pip install <the same wheel URL>`.

```python
import gascoigne

gascoigne.init(agent="my-app")
search = gascoigne.wrap_tool(search)      # any tool function returning str
# or: gascoigne.auto()                    # opt in to MCP and LangChain tools
```

## TypeScript

npm does not install remote tarballs by URL, so download both and install the files. They belong
together: `ai-sdk` depends on `sdk`.

```sh
base=https://github.com/gascoigne-ai/gascoigne-sdk/releases/download/ts-v0.1.1
curl -sLO $base/gascoigne-ai-sdk-0.1.1.tgz -O $base/gascoigne-ai-ai-sdk-0.1.1.tgz
npm install ./gascoigne-ai-sdk-0.1.1.tgz ./gascoigne-ai-ai-sdk-0.1.1.tgz
```

Or from GitHub Packages (needs a token, see [`github-packages.md`](github-packages.md)):
`npm install @gascoigne-ai/sdk @gascoigne-ai/ai-sdk`.

```ts
import { init, wrapTool } from "@gascoigne-ai/sdk";
import { wrapTools } from "@gascoigne-ai/ai-sdk";   // Vercel AI SDK tools

init({ agent: "my-app" });
const search = wrapTool(searchFn, "search");
```

## Go

```sh
go get github.com/gascoigne-ai/gascoigne-sdk/go@v0.1.0
```

If `go get` says the module is not found right after a release, the Go module proxy cached an earlier
miss. Retry in a few minutes, or fetch once without it: `GOPROXY=direct GOSUMDB=off go get ...`.

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

Download the two packages from the release into a folder and add it as a NuGet source next to
nuget.org, in a `nuget.config` beside your project:

```sh
base=https://github.com/gascoigne-ai/gascoigne-sdk/releases/download/dotnet-v0.1.1
mkdir packages && cd packages
curl -sLO $base/Gascoigne.0.1.1.nupkg -O $base/Gascoigne.Extensions.AI.0.1.1.nupkg
```

```xml
<configuration>
  <packageSources>
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />
    <add key="gascoigne" value="./packages" />
  </packageSources>
</configuration>
```

```sh
dotnet add package Gascoigne.Extensions.AI --version 0.1.1   # brings in Gascoigne too
```

Or use GitHub Packages ([`github-packages.md`](github-packages.md)).

```csharp
using var gascoigne = new GascoigneClient(new GascoigneOptions { Agent = "my-app" });
string shortText = await gascoigne.OptimizeAsync(toolOutput, new Attrs { Tool = "search" });
// Microsoft.Extensions.AI: .UseFunctionInvocation(configure: c => c.UseGascoigne(gascoigne))
```

## Rust

```sh
cargo add gascoigne --git https://github.com/gascoigne-ai/gascoigne-sdk --tag rust-v0.1.0
```

```rust
let rt = gascoigne::Runtime::new("my-app");
let short = rt.optimize(&tool_output, &gascoigne::Attrs::tool("search"));
```

## Check that it works

Run a demo ([`demos/README.md`](../demos/README.md)), or call `optimize` on a long log. With the CLI
missing you see one warning, `gascoigne-cli not found on PATH`, and the text comes back unchanged.
