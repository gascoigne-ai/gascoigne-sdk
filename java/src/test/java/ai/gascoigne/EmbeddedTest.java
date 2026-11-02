package ai.gascoigne;

import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class EmbeddedTest {
    private static final Path LIB = Path.of("../native/dist/libgascoigne.so").toAbsolutePath();

    @Test void missingLibraryThrowsAndNamesWhereItLooked() {
        var builder = Gascoigne.builder()
                .embedded(Settings.defaults())
                .library("/nonexistent/libgascoigne.so");
        var e = assertThrows(IllegalStateException.class, builder::build);
        assertTrue(e.getMessage().contains("libgascoigne not found"));
    }

    @Test void optimizesAndReturnsTheOriginal(@TempDir Path dir) {
        assumeTrue(Files.exists(LIB), "build native/ first");
        var settings = Settings.defaults()
                .withoutUserFile()
                .withConfig("extensions:\n  ledger:\n    path: " + dir.resolve("l.db") + "\n");
        var g = Gascoigne.builder().embedded(settings).library(LIB.toString()).build();
        String raw = "INFO request served path=/api/items status=200 ms=12\n".repeat(400);
        Result res = g.optimizeResult(raw, Attrs.tool("bash"));
        assertTrue(res.outTokens() < res.rawTokens());
        assertFalse(res.rawId().isEmpty());
        assertEquals(raw, g.raw(res.rawId()));
        assertTrue(g.proxyBaseUrl("openai").isEmpty());
        g.close();
    }

    @Test void unpackIsIdempotentAndChecksContent(@TempDir Path dir) throws Exception {
        byte[] gz = gzip("library bytes");
        String saved = System.getProperty("java.io.tmpdir");
        System.setProperty("java.io.tmpdir", dir.toString());
        try {
            checkUnpack(gz);
        } finally {
            System.setProperty("java.io.tmpdir", saved);
        }
    }

    private static void checkUnpack(byte[] gz) throws Exception {
        java.io.File first = NativeEngine.unpack(new java.io.ByteArrayInputStream(gz), "lib.so");
        assertEquals("library bytes", Files.readString(first.toPath()));
        assertTrue(first.getParentFile().getName().startsWith("gascoigne-native-"));
        assertEquals(first, NativeEngine.unpack(new java.io.ByteArrayInputStream(gz), "lib.so"));
        // A file replaced behind our back is rewritten, never loaded as is.
        Files.writeString(first.toPath(), "tampered");
        java.io.File again = NativeEngine.unpack(new java.io.ByteArrayInputStream(gz), "lib.so");
        assertEquals("library bytes", Files.readString(again.toPath()));
    }

    @Test void bundledLibraryLoadsFromTmp(@TempDir Path dir) {
        assumeTrue(
                getClass().getClassLoader().getResource(
                        "gascoigne/native/" + NativeEngine.platformKey() + "/libgascoigne.so.gz")
                        != null,
                "run scripts/bundle_native.py");
        var settings = Settings.defaults()
                .withoutUserFile()
                .withConfig("extensions:\n  ledger:\n    path: " + dir.resolve("l.db") + "\n");
        var g = Gascoigne.builder().embedded(settings).build();
        String raw = "INFO request served path=/api/items status=200 ms=12\n".repeat(400);
        assertFalse(g.optimizeResult(raw, Attrs.tool("bash")).rawId().isEmpty());
        g.close();
    }

    private static byte[] gzip(String text) throws java.io.IOException {
        var out = new java.io.ByteArrayOutputStream();
        try (var z = new java.util.zip.GZIPOutputStream(out)) {
            z.write(text.getBytes(java.nio.charset.StandardCharsets.UTF_8));
        }
        return out.toByteArray();
    }
}
