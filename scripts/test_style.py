"""Tests for scripts/style.py --params. Run: python3 -m unittest discover -s scripts."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import style


def flagged(suffix: str, text: str) -> list[str]:
    return [name for _, name in style.LANGUAGES[suffix].detect(text)]


def run_params(*args: str) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = style.main(["style.py", *args])
    return code, out.getvalue()


# Signature shapes taken from the SDK sources and demos.
BAD = {
    ".py": [("def f(r):\n    return r\n", ["r"]), ("sort(key=lambda m: m)\n", ["m"])],
    ".ts": [
        ("function f(r: Request) {\n}\n", ["r"]),
        ('const pad = (n: number) => String(n).padStart(2, "0");\n', ["n"]),
        ("const count = (n: number) => n.toLocaleString();\n", ["n"]),
        ("items.map((m) => m);\n", ["m"]),
        ("items.map(x => x);\n", ["x"]),
    ],
    ".go": [
        ("func Do(r *Request) error {\n}\n", ["r"]),
        ("func(a, b int) int {\n}\n", ["a", "b"]),
    ],
    ".rs": [
        ("fn run(r: &Req) -> String {\n}\n", ["r"]),
        ("let next = |x| x + 1;\n", ["x"]),
        (".map(|e| e.len())\n", ["e"]),
    ],
    ".java": [
        ("void send(Request r) {\n}\n", ["r"]),
        (".filter(e -> e.rawTokens() > 0)\n", ["e"]),
        ("lines().map(m -> m.trim())\n", ["m"]),
    ],
    ".cs": [
        ("public static void Send(Request r)\n{\n}\n", ["r"]),
        (".Select(m => Line(m))\n", ["m"]),
    ],
}

ALLOWED = {
    ".py": "def f(request):\n    return lambda message: message\n",
    ".ts": "function f(request: Request) {\n}\nitems.map((message) => message);\n",
    ".go": "func Report(rt *Runtime, before string, res Result) {\n}\n",
    ".rs": "fn run(request: &Req) -> String {\n}\nlet next = |value| value + 1;\n",
    ".java": "void send(Request request) {\n}\nitems.map(message -> message);\n",
    ".cs": "public static void Send(string original, Result result)\n{\n}\nx.Select(i => i);\n",
}


class DetectTest(unittest.TestCase):
    def test_bad_snippet_per_language(self):
        for suffix, cases in BAD.items():
            for text, want in cases:
                with self.subTest(suffix=suffix, text=text):
                    self.assertEqual(flagged(suffix, text), want)

    def test_allowed_snippet_per_language(self):
        for suffix, text in ALLOWED.items():
            with self.subTest(suffix=suffix):
                self.assertEqual(flagged(suffix, text), [])

    def test_underscore_is_exempt_per_language(self):
        snippets = {
            ".py": "def f(_):\n    pass\n",
            ".ts": "items.map((_, index) => index);\n",
            ".go": "func Do(_ int) {\n}\n",
            ".rs": "fn run(_: u8) {\n}\n",
            ".java": "items.map(_ -> 1);\n",
            ".cs": "items.Select(_ => 1);\n",
        }
        for suffix, text in snippets.items():
            with self.subTest(suffix=suffix):
                self.assertEqual(flagged(suffix, text), [])

    def test_go_test_types_are_exempt(self):
        for kind in ("T", "B", "F", "TB"):
            text = f"func TestX(t *testing.{kind}) {{\n}}\n"
            with self.subTest(kind=kind):
                self.assertEqual(flagged(".go", text), [])
        self.assertEqual(flagged(".go", "func Do(t int) {\n}\n"), ["t"])

    def test_go_receiver_is_exempt(self):
        text = "func (c *Client) Do(r int) error {\n}\n"
        self.assertEqual(flagged(".go", text), ["r"])

    def test_go_grouped_parameters_flag_each_name(self):
        self.assertEqual(flagged(".go", "func Do(a, b int, name string) {\n}\n"), ["a", "b"])

    def test_go_types_only_list_is_ignored(self):
        self.assertEqual(flagged(".go", "func Observe() func(string, Result) {\n}\n"), [])

    def test_go_variadic_counts(self):
        self.assertEqual(flagged(".go", "func Do(v ...string) {\n}\n"), ["v"])

    def test_type_parameters_are_exempt(self):
        snippets = {
            ".go": "func Map[T any](items []T) []T {\n}\n",
            ".ts": "function first<T>(items: T[]): T {\n}\n",
            ".rs": "fn first<T>(items: Vec<T>) -> T {\n}\n",
            ".java": "<T> T first(List<T> items) {\n}\n",
            ".cs": "public T First<T>(List<T> items)\n{\n}\n",
        }
        for suffix, text in snippets.items():
            with self.subTest(suffix=suffix):
                self.assertEqual(flagged(suffix, text), [])

    def test_loop_index_names_are_exempt(self):
        self.assertEqual(flagged(".ts", "items.map((i) => i);\n"), [])
        self.assertEqual(flagged(".ts", "items.map((j) => j);\n"), [])
        self.assertEqual(flagged(".ts", "items.map((x) => x);\n"), ["x"])

    def test_rust_bitwise_or_is_not_a_closure(self):
        self.assertEqual(flagged(".rs", "let flags = a | b;\nlet ok = a || b;\n"), [])

    def test_comments_and_strings_are_ignored(self):
        snippets = {
            ".py": 'text = "def f(r): pass"\n# def g(m): pass\n',
            ".ts": 'const text = "function f(r) {}";\n// (m) => m\n',
            ".go": 'var text = "func(a int) {}"\n// func Do(r int) {\n',
            ".rs": 'let text = "|x| x";\n// fn run(r: u8) {\n',
            ".java": 'String text = "m -> m";\n// void send(Request r) {\n',
            ".cs": 'var text = "m => m";\n// void Send(Request r)\n',
        }
        for suffix, text in snippets.items():
            with self.subTest(suffix=suffix):
                self.assertEqual(flagged(suffix, text), [])

    def test_line_numbers_survive_multiline_comments(self):
        text = "/*\n one\n two\n*/\nfunction f(r: Request) {\n}\n"
        self.assertEqual(style.LANGUAGES[".ts"].detect(text), [(5, "r")])

    def test_python_syntax_error_is_reported(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "broken.py").write_text("def f(:\n")
            code, out = run_params("--params", root)
        self.assertEqual(code, 1)
        self.assertIn("broken.py: cannot parse (", out)


class CliTest(unittest.TestCase):
    def test_violating_tree_exits_one_with_path_line_output(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "a.ts").write_text("\nfunction f(r: Request) {\n}\n")
            code, out = run_params("--params", root)
            path = Path(root, "a.ts")
        self.assertEqual(code, 1)
        self.assertEqual(out.strip(), f"{path}:2: one-letter parameter 'r' (typescript)")

    def test_clean_tree_exits_zero(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "a.py").write_text("def f(request):\n    pass\n")
            code, out = run_params("--params", root)
        self.assertEqual((code, out.strip()), (0, "params ok"))

    def test_unknown_suffix_is_skipped(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "notes.txt").write_text("def f(r):\n")
            code, _ = run_params("--params", root)
        self.assertEqual(code, 0)

    def test_file_argument_and_sorted_output(self):
        with tempfile.TemporaryDirectory() as root:
            first = Path(root, "b.py")
            second = Path(root, "a.py")
            first.write_text("def f(r):\n    pass\n")
            second.write_text("def f(m):\n    pass\n")
            code, out = run_params("--params", str(first), str(second))
        self.assertEqual(code, 1)
        lines = out.strip().splitlines()
        self.assertEqual([line.split(":")[0] for line in lines], [str(second), str(first)])

    def test_no_paths_is_usage_error(self):
        code, out = run_params("--params")
        self.assertEqual(code, 2)
        self.assertIn("usage", out.lower())

    def test_plain_run_does_not_check_params(self):
        self.assertFalse(style.wants_params(["style.py"]))
        self.assertTrue(style.wants_params(["style.py", "--params", "x"]))


if __name__ == "__main__":
    unittest.main()
