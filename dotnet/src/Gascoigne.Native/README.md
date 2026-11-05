# Gascoigne.Native.<rid>

Adds the native variant to the `Gascoigne` SDK: the engine runs inside your process, with no server
and no CLI. Reference the package of your system next to `Gascoigne` (`Gascoigne.Native.linux-x64`,
`linux-arm64`, `osx-x64`, `osx-arm64`, `win-x64`), for example with a condition, and select it:

```xml
<PackageReference Include="Gascoigne.Native.linux-x64" Version="0.11.0"
                  Condition="$([MSBuild]::IsOSPlatform('Linux'))" />
```

```csharp
var client = new GascoigneClient(new GascoigneOptions { Embedded = new EmbeddedSettings() });
```

The library for your platform is unpacked to the temporary directory on first use. This package
holds data only; see `spec/native.md` in the repository.
