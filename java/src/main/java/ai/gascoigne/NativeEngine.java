package ai.gascoigne;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.jna.Library;
import com.sun.jna.Native;
import com.sun.jna.Pointer;
import com.sun.jna.ptr.PointerByReference;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Map;
import java.util.zip.GZIPInputStream;

/**
 * The embedded variant: libgascoigne called through JNA, an optional dependency. Loading this
 * class without JNA on the class path throws {@link LinkageError}, which {@link Gascoigne} catches.
 */
final class NativeEngine implements AutoCloseable {
    private static final int ABI = 2;
    private static final ObjectMapper JSON = new ObjectMapper();

    /** The C ABI of spec/native.md. */
    interface Lib extends Library {
        int gascoigne_abi_version();

        long gascoigne_open(String options, PointerByReference err);

        Pointer gascoigne_optimize(long handle, String request, PointerByReference err);

        Pointer gascoigne_raw(long handle, String id, PointerByReference err);

        Pointer gascoigne_stats(long handle, String query, PointerByReference err);

        Pointer gascoigne_recent(long handle, String query, PointerByReference err);

        Pointer gascoigne_costs(long handle, String query, PointerByReference err);

        void gascoigne_close(long handle);

        void gascoigne_free(Pointer s);
    }

    private final Lib lib;
    private final long handle;

    NativeEngine(Settings settings, String path) throws Exception {
        java.util.List<String> looked = new java.util.ArrayList<>();
        File file = path != null ? new File(path) : findLibrary(looked);
        if (file == null || !file.isFile()) {
            throw new IllegalStateException("libgascoigne not found; looked in: "
                    + String.join(", ", looked)
                    + ". Install it in one of those places or add the gascoigne-native dependency");
        }
        lib = Native.load(
                file.getPath(), Lib.class, Map.of(Library.OPTION_STRING_ENCODING, "UTF-8"));
        if (lib.gascoigne_abi_version() != ABI) {
            throw new IllegalStateException(file + " speaks another ABI than " + ABI);
        }
        PointerByReference err = new PointerByReference();
        handle = lib.gascoigne_open(JSON.writeValueAsString(settings), err);
        if (handle == 0) {
            throw new IllegalStateException(take(err));
        }
    }

    private static final String[] LIBRARY_NAMES =
            {"libgascoigne.so", "libgascoigne.dylib", "gascoigne.dll"};

    /** {@code <os>-<arch>} as the bundle names its folders. */
    static String platformKey() {
        String os = System.getProperty("os.name").toLowerCase();
        String arch = System.getProperty("os.arch").toLowerCase();
        String name = os.contains("win") ? "windows" : os.contains("mac") ? "darwin" : "linux";
        return name + "-" + (arch.equals("x86_64") || arch.equals("amd64") ? "amd64" : "arm64");
    }

    /**
     * Unpacks a gzip-compressed library into the temp directory and returns the file to load. The
     * folder is named by the library's hash, so this is idempotent and an existing file is trusted
     * only when its content matches; the write goes through a temporary name and a rename.
     */
    static File unpack(InputStream gzipped, String name) throws IOException {
        byte[] data;
        try (InputStream in = new GZIPInputStream(gzipped)) {
            data = in.readAllBytes();
        }
        String digest = sha256(data);
        String root = System.getenv("GASCOIGNE_LIB_DIR");
        Path base = root != null && !root.isEmpty()
                ? Path.of(root)
                : Path.of(System.getProperty("java.io.tmpdir"));
        Path folder = base.resolve("gascoigne-native-" + digest);
        Path target = folder.resolve(name);
        if (Files.isRegularFile(target) && sha256(Files.readAllBytes(target)).equals(digest)) {
            return target.toFile();
        }
        Files.createDirectories(folder);
        try {
            Files.setPosixFilePermissions(folder, PosixFilePermissions.fromString("rwx------"));
        } catch (UnsupportedOperationException ignored) {
            // not a POSIX file system
        }
        Path partial = Files.createTempFile(folder, ".unpack", ".tmp");
        Files.write(partial, data);
        partial.toFile().setExecutable(true, true);
        Files.move(partial, target, java.nio.file.StandardCopyOption.REPLACE_EXISTING,
                java.nio.file.StandardCopyOption.ATOMIC_MOVE);
        return target.toFile();
    }

    private static String sha256(byte[] data) throws IOException {
        try {
            byte[] sum = MessageDigest.getInstance("SHA-256").digest(data);
            return HexFormat.of().formatHex(sum).substring(0, 16);
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new IOException(e);
        }
    }

    /** This platform's entry of the gascoigne-native jar, unpacked; null when it is not there. */
    private static File bundled() throws IOException {
        for (String name : LIBRARY_NAMES) {
            String resource = "gascoigne/native/" + platformKey() + "/" + name + ".gz";
            InputStream in = NativeEngine.class.getClassLoader().getResourceAsStream(resource);
            if (in != null) {
                try (in) {
                    return unpack(in, name);
                }
            }
        }
        return null;
    }

    /** Where an installed library may live (see spec/native.md). */
    private static java.util.List<Path> systemDirs() {
        java.util.List<Path> dirs = new java.util.ArrayList<>();
        String extra = System.getenv("GASCOIGNE_LIB_PATH");
        if (extra != null) {
            for (String d : extra.split(File.pathSeparator)) {
                if (!d.isEmpty()) {
                    dirs.add(Path.of(d));
                }
            }
        }
        String bin = System.getenv("GASCOIGNE_BIN");
        if (bin != null && !bin.isEmpty() && Path.of(bin).getParent() != null) {
            dirs.add(Path.of(bin).getParent());
        }
        Path home = Path.of(System.getProperty("user.home"));
        String os = System.getProperty("os.name").toLowerCase();
        if (os.contains("win")) {
            for (String v : new String[] {"LOCALAPPDATA", "ProgramFiles"}) {
                if (System.getenv(v) != null) {
                    dirs.add(Path.of(System.getenv(v), "gascoigne"));
                }
            }
        } else if (os.contains("mac")) {
            dirs.addAll(java.util.List.of(home.resolve(".local/lib"), Path.of("/usr/local/lib"),
                    Path.of("/opt/homebrew/lib")));
        } else {
            String multiarch = (platformKey().endsWith("arm64") ? "aarch64" : "x86_64")
                    + "-linux-gnu";
            dirs.addAll(java.util.List.of(home.resolve(".local/lib"), Path.of("/usr/local/lib"),
                    Path.of("/usr/lib"), Path.of("/usr/lib64"), Path.of("/usr/lib", multiarch),
                    Path.of("/opt/gascoigne/lib")));
        }
        return dirs;
    }

    /**
     * Finds the library: {@code $GASCOIGNE_LIB}, the system directories, then the gascoigne-native
     * dependency unpacked to a temp dir. {@code looked} receives where it searched.
     */
    private static File findLibrary(java.util.List<String> looked) throws IOException {
        String env = System.getenv("GASCOIGNE_LIB");
        if (env != null && !env.isEmpty()) {
            looked.add("$GASCOIGNE_LIB=" + env);
            File f = new File(env);
            return f.isFile() ? f : null;
        }
        for (Path dir : systemDirs()) {
            looked.add(dir.toString());
            for (String name : LIBRARY_NAMES) {
                if (Files.isRegularFile(dir.resolve(name))) {
                    return dir.resolve(name).toFile();
                }
            }
        }
        if (!"off".equals(System.getenv("GASCOIGNE_UNPACK"))) {
            looked.add("the gascoigne-native dependency");
            return bundled();
        }
        return null;
    }

    /** Copies and releases a string the library returned. */
    private String take(PointerByReference ref) {
        return take(ref.getValue(), "failed");
    }

    private String take(Pointer p, String fallback) {
        if (p == null) {
            return fallback;
        }
        try {
            return new String(p.getString(0, "UTF-8").getBytes(StandardCharsets.UTF_8),
                    StandardCharsets.UTF_8);
        } finally {
            lib.gascoigne_free(p);
        }
    }

    Result optimize(OptimizeRequest request) throws Exception {
        PointerByReference err = new PointerByReference();
        Pointer out = lib.gascoigne_optimize(handle, JSON.writeValueAsString(request), err);
        if (out == null) {
            throw new IllegalStateException(take(err));
        }
        return JSON.readValue(take(out, ""), Result.class);
    }

    String raw(String id) {
        PointerByReference err = new PointerByReference();
        Pointer out = lib.gascoigne_raw(handle, id, err);
        if (out == null) {
            take(err);
            return "";
        }
        return take(out, "");
    }

    /** The totals as the library's JSON list; throws when the query is bad. */
    String stats(String queryJson) {
        PointerByReference err = new PointerByReference();
        return result(lib.gascoigne_stats(handle, queryJson, err), err);
    }

    /** The recorded runs as the library's JSON list. */
    String recent(String queryJson) {
        PointerByReference err = new PointerByReference();
        return result(lib.gascoigne_recent(handle, queryJson, err), err);
    }

    /** The tokens saved, priced, as the library's JSON object. */
    String costs(String queryJson) {
        PointerByReference err = new PointerByReference();
        return result(lib.gascoigne_costs(handle, queryJson, err), err);
    }

    private String result(Pointer out, PointerByReference err) {
        if (out == null) {
            throw new IllegalStateException(take(err));
        }
        return take(out, "");
    }

    @Override
    public void close() {
        lib.gascoigne_close(handle);
    }
}
