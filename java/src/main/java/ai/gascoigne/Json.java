package ai.gascoigne;

import java.util.LinkedHashMap;
import java.util.Map;

/** The little JSON the protocol needs: flat objects of strings and numbers. */
final class Json {
    private Json() {}

    static String encode(Map<String, String> fields) {
        var sb = new StringBuilder("{");
        fields.forEach((k, v) -> {
            if (sb.length() > 1) sb.append(',');
            sb.append(quote(k)).append(':').append(quote(v));
        });
        return sb.append('}').toString();
    }

    private static String quote(String s) {
        var sb = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            switch (c) {
                case '"' -> sb.append("\\\"");
                case '\\' -> sb.append("\\\\");
                case '\n' -> sb.append("\\n");
                case '\r' -> sb.append("\\r");
                case '\t' -> sb.append("\\t");
                default -> {
                    if (c < 0x20) sb.append(String.format("\\u%04x", (int) c));
                    else sb.append(c);
                }
            }
        }
        return sb.append('"').toString();
    }

    /** Parses a flat object; nested values are skipped. Returns null when it is not an object. */
    static Map<String, String> decode(String json) {
        var out = new LinkedHashMap<String, String>();
        int[] i = {0};
        skipWs(json, i);
        if (i[0] >= json.length() || json.charAt(i[0]++) != '{') return null;
        while (true) {
            skipWs(json, i);
            if (i[0] >= json.length()) return null;
            if (json.charAt(i[0]) == '}') return out;
            if (json.charAt(i[0]) == ',') { i[0]++; continue; }
            String key = string(json, i);
            skipWs(json, i);
            if (key == null || i[0] >= json.length() || json.charAt(i[0]++) != ':') return null;
            skipWs(json, i);
            if (i[0] >= json.length()) return null;
            char c = json.charAt(i[0]);
            if (c == '"') {
                String v = string(json, i);
                if (v == null) return null;
                out.put(key, v);
            } else if (c == '{' || c == '[') {
                skipNested(json, i);
            } else {
                int start = i[0];
                while (i[0] < json.length() && ",}".indexOf(json.charAt(i[0])) < 0) i[0]++;
                out.put(key, json.substring(start, i[0]).trim());
            }
        }
    }

    private static void skipWs(String s, int[] i) {
        while (i[0] < s.length() && Character.isWhitespace(s.charAt(i[0]))) i[0]++;
    }

    private static void skipNested(String s, int[] i) {
        int depth = 0;
        boolean inStr = false;
        for (; i[0] < s.length(); i[0]++) {
            char c = s.charAt(i[0]);
            if (inStr) {
                if (c == '\\') i[0]++;
                else if (c == '"') inStr = false;
            } else if (c == '"') inStr = true;
            else if (c == '{' || c == '[') depth++;
            else if ((c == '}' || c == ']') && --depth == 0) { i[0]++; return; }
        }
    }

    private static String string(String s, int[] i) {
        if (i[0] >= s.length() || s.charAt(i[0]) != '"') return null;
        var sb = new StringBuilder();
        for (i[0]++; i[0] < s.length(); i[0]++) {
            char c = s.charAt(i[0]);
            if (c == '"') { i[0]++; return sb.toString(); }
            if (c != '\\') { sb.append(c); continue; }
            if (++i[0] >= s.length()) return null;
            switch (s.charAt(i[0])) {
                case 'n' -> sb.append('\n');
                case 'r' -> sb.append('\r');
                case 't' -> sb.append('\t');
                case 'b' -> sb.append('\b');
                case 'f' -> sb.append('\f');
                case 'u' -> {
                    if (i[0] + 4 >= s.length()) return null;
                    sb.append((char) Integer.parseInt(s.substring(i[0] + 1, i[0] + 5), 16));
                    i[0] += 4;
                }
                default -> sb.append(s.charAt(i[0]));
            }
        }
        return null;
    }
}
