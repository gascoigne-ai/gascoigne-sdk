using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Gascoigne;

/// <summary>The embedded variant: libgascoigne loaded at run time (see spec/native.md).</summary>
internal sealed class NativeEngine : IDisposable
{
    private const int Abi = 2;

    private static bool EnvIs(string name, string value) =>
        Environment.GetEnvironmentVariable(name) == value;

    private static readonly JsonSerializerOptions Json = new()
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingDefault,
    };

    private readonly nint _lib;
    private readonly Open _open;
    private readonly Call _optimize;
    private readonly Call _raw;
    private readonly Call _stats;
    private readonly Call _recent;
    private readonly Call _costs;
    private readonly Close _close;
    private readonly Free _free;
    private readonly ulong _handle;

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate int Version();

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate ulong Open(nint options, out nint err);

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate nint Call(ulong handle, nint arg, out nint err);

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate void Close(ulong handle);

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate void Free(nint s);

    internal NativeEngine(EmbeddedSettings settings, string? path)
    {
        var looked = new List<string>();
        path ??= FindLibrary(looked);
        if (path is null || !File.Exists(path))
        {
            throw new FileNotFoundException("libgascoigne not found; looked in: "
                + string.Join(", ", looked)
                + ". Install it in one of those places or add the Gascoigne.Native.<rid> package");
        }

        _lib = NativeLibrary.Load(path);
        try
        {
            if (Bind<Version>("gascoigne_abi_version")() != Abi)
            {
                throw new InvalidOperationException($"{path} speaks another ABI than {Abi}");
            }

            _open = Bind<Open>("gascoigne_open");
            _optimize = Bind<Call>("gascoigne_optimize");
            _raw = Bind<Call>("gascoigne_raw");
            _stats = Bind<Call>("gascoigne_stats");
            _recent = Bind<Call>("gascoigne_recent");
            _costs = Bind<Call>("gascoigne_costs");
            _close = Bind<Close>("gascoigne_close");
            _free = Bind<Free>("gascoigne_free");
            _handle = OpenHandle(settings);
        }
        catch
        {
            NativeLibrary.Free(_lib);
            throw;
        }
    }

    /// <summary>The folder name the bundle uses: <c>os-arch</c>.</summary>
    internal static string PlatformKey()
    {
        var os = OperatingSystem.IsWindows() ? "windows"
            : OperatingSystem.IsMacOS() ? "darwin" : "linux";
        var arch = RuntimeInformation.OSArchitecture == Architecture.Arm64 ? "arm64" : "amd64";
        return $"{os}-{arch}";
    }

    /// <summary>
    /// Unpacks a gzip-compressed library into the temp directory and returns the file to load. The
    /// folder is named by the library's hash, so this is idempotent and an existing file is
    /// trusted only when its content matches; the write goes through a temporary name and a rename.
    /// </summary>
    internal static string Unpack(Stream gzipped, string name)
    {
        using var gz = new System.IO.Compression.GZipStream(
            gzipped, System.IO.Compression.CompressionMode.Decompress);
        using var buffer = new MemoryStream();
        gz.CopyTo(buffer);
        var data = buffer.ToArray();
        var digest = Digest(data);
        var root = Environment.GetEnvironmentVariable("GASCOIGNE_LIB_DIR");
        var folder = Path.Combine(
            string.IsNullOrEmpty(root) ? Path.GetTempPath() : root, $"gascoigne-native-{digest}");
        var target = Path.Combine(folder, name);
        if (File.Exists(target) && Digest(File.ReadAllBytes(target)) == digest)
        {
            return target;
        }

        Directory.CreateDirectory(folder);
        if (!OperatingSystem.IsWindows())
        {
            File.SetUnixFileMode(folder, UnixFileMode.UserRead | UnixFileMode.UserWrite
                | UnixFileMode.UserExecute);
        }

        var partial = Path.Combine(folder, $".{Environment.ProcessId}.tmp");
        File.WriteAllBytes(partial, data);
        File.Move(partial, target, overwrite: true);
        return target;
    }

    private static string Digest(byte[] data) =>
        Convert.ToHexString(SHA256.HashData(data))[..16];

    /// <summary>This platform's entry of the Gascoigne.Native package, unpacked, or null.</summary>
    private static string? Bundled()
    {
        Assembly assembly;
        try
        {
            assembly = Assembly.Load("Gascoigne.Native");
        }
        catch (FileNotFoundException)
        {
            return null;
        }

        foreach (var name in new[] { "libgascoigne.so", "libgascoigne.dylib", "gascoigne.dll" })
        {
            using var stream = assembly.GetManifestResourceStream(
                $"gascoigne/native/{PlatformKey()}/{name}.gz");
            if (stream is not null)
            {
                return Unpack(stream, name);
            }
        }

        return null;
    }

    private static readonly string[] LibraryNames =
        ["libgascoigne.so", "libgascoigne.dylib", "gascoigne.dll"];

    /// <summary>Where an installed library may live (see spec/native.md).</summary>
    private static List<string> SystemDirs()
    {
        var dirs = new List<string>();
        var extra = Environment.GetEnvironmentVariable("GASCOIGNE_LIB_PATH");
        if (!string.IsNullOrEmpty(extra))
        {
            dirs.AddRange(extra.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries));
        }

        var bin = Environment.GetEnvironmentVariable("GASCOIGNE_BIN");
        if (!string.IsNullOrEmpty(bin) && Path.GetDirectoryName(bin) is { Length: > 0 } beside)
        {
            dirs.Add(beside);
        }

        var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        if (OperatingSystem.IsWindows())
        {
            foreach (var variable in new[] { "LOCALAPPDATA", "ProgramFiles" })
            {
                if (Environment.GetEnvironmentVariable(variable) is { Length: > 0 } root)
                {
                    dirs.Add(Path.Combine(root, "gascoigne"));
                }
            }
        }
        else if (OperatingSystem.IsMacOS())
        {
            dirs.AddRange(
                [Path.Combine(home, ".local/lib"), "/usr/local/lib", "/opt/homebrew/lib"]);
        }
        else
        {
            var arch = RuntimeInformation.OSArchitecture == Architecture.Arm64
                ? "aarch64" : "x86_64";
            dirs.AddRange([
                Path.Combine(home, ".local/lib"), "/usr/local/lib", "/usr/lib", "/usr/lib64",
                $"/usr/lib/{arch}-linux-gnu", "/opt/gascoigne/lib",
            ]);
        }

        return dirs;
    }

    /// <summary>
    /// Finds the library: <c>$GASCOIGNE_LIB</c>, the system directories, then the
    /// Gascoigne.Native.* dependency unpacked to a temp dir. <paramref name="looked"/> receives
    /// where it searched.
    /// </summary>
    private static string? FindLibrary(List<string> looked)
    {
        var env = Environment.GetEnvironmentVariable("GASCOIGNE_LIB");
        if (!string.IsNullOrEmpty(env))
        {
            looked.Add($"$GASCOIGNE_LIB={env}");
            return File.Exists(env) ? env : null;
        }

        foreach (var dir in SystemDirs())
        {
            looked.Add(dir);
            var found = LibraryNames.Select(n => Path.Combine(dir, n)).FirstOrDefault(File.Exists);
            if (found is not null)
            {
                return found;
            }
        }

        if (!EnvIs("GASCOIGNE_UNPACK", "off"))
        {
            looked.Add("the Gascoigne.Native.<rid> package");
            return Bundled();
        }

        return null;
    }

    private T Bind<T>(string symbol) where T : Delegate =>
        Marshal.GetDelegateForFunctionPointer<T>(NativeLibrary.GetExport(_lib, symbol));

    private ulong OpenHandle(EmbeddedSettings settings)
    {
        var options = Marshal.StringToCoTaskMemUTF8(JsonSerializer.Serialize(settings, Json));
        try
        {
            var handle = _open(options, out var err);
            return handle != 0 ? handle : throw new InvalidOperationException(Take(err));
        }
        finally
        {
            Marshal.FreeCoTaskMem(options);
        }
    }

    /// <summary>Copies and releases a string the library returned.</summary>
    private string Take(nint ptr)
    {
        if (ptr == 0)
        {
            return "failed";
        }

        try
        {
            return Marshal.PtrToStringUTF8(ptr) ?? "";
        }
        finally
        {
            _free(ptr);
        }
    }

    private string Invoke(Call call, string arg)
    {
        var bytes = Marshal.StringToCoTaskMemUTF8(arg);
        try
        {
            var outPtr = call(_handle, bytes, out var err);
            return outPtr != 0 ? Take(outPtr) : throw new InvalidOperationException(Take(err));
        }
        finally
        {
            Marshal.FreeCoTaskMem(bytes);
        }
    }

    internal string Optimize(string requestJson) => Invoke(_optimize, requestJson);

    internal string Raw(string id) => Invoke(_raw, id);

    /// <summary>Totals per group, as the library's JSON list.</summary>
    internal string Stats(string queryJson) => Invoke(_stats, queryJson);

    /// <summary>Recorded runs, as the library's JSON list.</summary>
    internal string Recent(string queryJson) => Invoke(_recent, queryJson);

    /// <summary>The tokens saved, priced, as the library's JSON object.</summary>
    internal string Costs(string queryJson) => Invoke(_costs, queryJson);

    public void Dispose()
    {
        _close(_handle);
        NativeLibrary.Free(_lib);
    }
}
