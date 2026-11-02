using Gascoigne;
using Xunit;

public sealed class EmbeddedTests
{
    private static readonly string Lib = Path.GetFullPath(
        Path.Combine(AppContext.BaseDirectory, "../../../../../../native/dist/libgascoigne.so"));

    [Fact]
    public void MissingLibraryThrowsAndNamesWhereItLooked()
    {
        var e = Assert.Throws<FileNotFoundException>(() => new GascoigneClient(
            new GascoigneOptions
            {
                Embedded = new EmbeddedSettings(),
                Library = "/nonexistent/libgascoigne.so",
            }));
        Assert.Contains("libgascoigne not found", e.Message);
    }

    [Fact]
    public async Task OptimizesAndReturnsTheOriginal()
    {
        if (!File.Exists(Lib))
        {
            return;
        }

        var db = Path.Combine(Path.GetTempPath(), $"gas-dotnet-{Environment.ProcessId}.db");
        using var client = new GascoigneClient(new GascoigneOptions
        {
            Library = Lib,
            Embedded = new EmbeddedSettings
            {
                IgnoreUserFile = true,
                Config = $"extensions:\n  ledger:\n    path: {db}\n",
            },
        });
        var raw = string.Concat(Enumerable.Repeat(
            "INFO request served path=/api/items status=200 ms=12\n", 400));
        var res = await client.OptimizeResultAsync(raw, new Attrs { Tool = "bash" });
        Assert.True(res.OutTokens < res.RawTokens);
        Assert.NotEmpty(res.RawId);
        Assert.Equal(raw, await client.RawAsync(res.RawId));
        Assert.Null(await client.ProxyBaseUrlAsync());
    }

    [Fact]
    public void UnpackIsIdempotentAndChecksContent()
    {
        var dir = Path.Combine(Path.GetTempPath(), $"gas-unpack-{Guid.NewGuid():N}");
        Environment.SetEnvironmentVariable("GASCOIGNE_LIB_DIR", dir);
        try
        {
            var first = NativeEngine.Unpack(Gzip("library bytes"), "lib.so");
            Assert.Equal("library bytes", File.ReadAllText(first));
            Assert.Contains("gascoigne-native-", first);
            Assert.Equal(first, NativeEngine.Unpack(Gzip("library bytes"), "lib.so"));
            // A file replaced behind our back is rewritten, never loaded as is.
            File.WriteAllText(first, "tampered");
            var again = NativeEngine.Unpack(Gzip("library bytes"), "lib.so");
            Assert.Equal("library bytes", File.ReadAllText(again));
        }
        finally
        {
            Environment.SetEnvironmentVariable("GASCOIGNE_LIB_DIR", null);
        }
    }

    [Fact]
    public async Task BundledLibraryLoadsFromTmp()
    {
        var bundle = typeof(Gascoigne.Native.Bundle).Assembly;
        if (bundle.GetManifestResourceNames().Length == 0)
        {
            return;
        }

        var dir = Path.Combine(Path.GetTempPath(), $"gas-bundle-{Guid.NewGuid():N}");
        Environment.SetEnvironmentVariable("GASCOIGNE_LIB_DIR", dir);
        try
        {
            using var client = new GascoigneClient(new GascoigneOptions
            {
                Embedded = new EmbeddedSettings
                {
                    IgnoreUserFile = true,
                    Config = $"extensions:\n  ledger:\n    path: {dir}/l.db\n",
                },
            });
            var raw = string.Concat(Enumerable.Repeat(
                "INFO request served path=/api/items status=200 ms=12\n", 400));
            var res = await client.OptimizeResultAsync(raw);
            Assert.NotEmpty(res.RawId);
        }
        finally
        {
            Environment.SetEnvironmentVariable("GASCOIGNE_LIB_DIR", null);
        }
    }

    private static MemoryStream Gzip(string text)
    {
        var output = new MemoryStream();
        using (var gz = new System.IO.Compression.GZipStream(
            output, System.IO.Compression.CompressionLevel.Optimal, leaveOpen: true))
        {
            gz.Write(System.Text.Encoding.UTF8.GetBytes(text));
        }

        output.Position = 0;
        return output;
    }
}
