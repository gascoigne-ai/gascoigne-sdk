package ai.gascoigne;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/** Picks the part of an original that a model asks for. */
final class Selection {
    private static final int MAX_LINES = 200;

    private Selection() {}

    /**
     * Numbered lines of {@code text}, narrowed by a regex per line and a range such as "10-20".
     * The result is capped so that asking for the original cannot undo the saving.
     */
    static String of(String text, String grep, String lines) {
        List<String> rows = text.lines().toList();
        int start = 1;
        int end = rows.size();
        if (!lines.isEmpty()) {
            String[] range = lines.split("-", 2);
            start = range[0].isEmpty() ? 1 : Integer.parseInt(range[0].trim());
            boolean open = range.length < 2 || range[1].isEmpty();
            end = open ? start : Integer.parseInt(range[1].trim());
        }
        Pattern pattern = grep.isEmpty() ? null : Pattern.compile(grep);
        List<String> kept = new ArrayList<>();
        for (int n = Math.max(start, 1); n <= Math.min(end, rows.size()); n++) {
            String row = rows.get(n - 1);
            if (pattern == null || pattern.matcher(row).find()) {
                kept.add(n + ": " + row);
            }
        }
        if (kept.size() > MAX_LINES) {
            int more = kept.size() - MAX_LINES;
            kept = new ArrayList<>(kept.subList(0, MAX_LINES));
            kept.add("... " + more + " more lines; narrow with grep or lines");
        }
        return String.join("\n", kept);
    }
}
