# GitHub Packages

Every `ts-v*`, `java-v*` and `dotnet-v*` release is also published to GitHub Packages, using the
workflow's own token. GitHub Packages has no registry for Python, Rust or Go, so those come from the
GitHub release assets (or PyPI, crates.io and the Go module proxy once published there).

GitHub Packages asks for authentication **even to install public packages**. Create a personal access
token (classic) with the `read:packages` scope and use it as the password below. In a GitHub Actions
workflow of this organization, `GITHUB_TOKEN` is enough.

## npm (`@gascoigne-ai/sdk`, `@gascoigne-ai/ai-sdk`)

```ini
# ~/.npmrc or the project's .npmrc
@gascoigne-ai:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=YOUR_TOKEN
```

```sh
npm install @gascoigne-ai/sdk
```

## Maven (`ai.gascoigne:gascoigne`, `ai.gascoigne:gascoigne-spring-ai`)

In `~/.m2/settings.xml`:

```xml
<settings>
  <activeProfiles><activeProfile>github</activeProfile></activeProfiles>
  <profiles>
    <profile>
      <id>github</id>
      <repositories>
        <repository><id>central</id><url>https://repo.maven.apache.org/maven2</url></repository>
        <repository>
          <id>github</id>
          <url>https://maven.pkg.github.com/gascoigne-ai/gascoigne-sdk</url>
        </repository>
      </repositories>
    </profile>
  </profiles>
  <servers>
    <server><id>github</id><username>YOUR_GITHUB_USER</username><password>YOUR_TOKEN</password></server>
  </servers>
</settings>
```

```xml
<dependency>
  <groupId>ai.gascoigne</groupId>
  <artifactId>gascoigne</artifactId>
  <version>0.1.1</version>
</dependency>
```

## NuGet (`Gascoigne`, `Gascoigne.Extensions.AI`)

```sh
dotnet nuget add source https://nuget.pkg.github.com/gascoigne-ai/index.json \
  --name github-gascoigne --username YOUR_GITHUB_USER --password YOUR_TOKEN \
  --store-password-in-clear-text
dotnet add package Gascoigne
```

## How the workflow publishes

| Registry | Step | Notes |
|---|---|---|
| npm | `npm publish` on the release's `.tgz` files, registry `https://npm.pkg.github.com` | the scope must equal the owner, hence `@gascoigne-ai` |
| Maven | `mvn deploy`, `distributionManagement` points at `https://maven.pkg.github.com/gascoigne-ai/gascoigne-sdk` | `artifactId` stays lower case |
| NuGet | `dotnet nuget push` to `https://nuget.pkg.github.com/gascoigne-ai/index.json` | `RepositoryUrl` links the package to this repo |
