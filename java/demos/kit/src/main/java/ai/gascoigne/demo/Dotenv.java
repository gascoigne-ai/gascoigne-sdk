package ai.gascoigne.demo;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/** Reads the nearest {@code .env} into system properties; real environment variables win. */
final class Dotenv {
    private Dotenv() {}

    static void load() {
        for (Path dir = Path.of("").toAbsolutePath(); dir != null; dir = dir.getParent()) {
            Path file = dir.resolve(".env");
            if (Files.isRegularFile(file)) {
                read(file);
                return;
            }
        }
    }

    private static void read(Path file) {
        try {
            List<String> lines = Files.readAllLines(file);
            for (String line : lines) {
                int eq = line.indexOf('=');
                if (line.isBlank() || line.startsWith("#") || eq < 0) {
                    continue;
                }
                String key = line.substring(0, eq).trim();
                String value = line.substring(eq + 1).trim().replaceAll("^[\"']|[\"']$", "");
                if (System.getenv(key) == null && !value.isEmpty()) {
                    System.setProperty(key, value);
                }
            }
        } catch (IOException e) {
            System.err.println("could not read " + file + ": " + e.getMessage());
        }
    }
}
