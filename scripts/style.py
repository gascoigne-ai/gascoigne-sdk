#!/usr/bin/env python3
"""Checks what linters do not: 100 columns, no trailing comments, ASCII-only source.

See .harness/code-style.md. Usage: scripts/style.py
The default run also rejects one-letter parameter names in the tracked sources.
Also: scripts/style.py --params <path>... reports them for any path: a file or a directory
searched recursively.
"""

import ast
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

MAX_COLS = 100
SOURCE = {".py", ".ts", ".go", ".rs", ".java", ".cs"}
# every other language here uses "//"
LINE_COMMENT = {".py": "#"}
STRING = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`[^`]*`')

# Names a parameter may have: unused, and loop indices.
ALLOWED_NAMES = frozenset({"_", "i", "j"})
# Go test types whose parameter may be t, b or f.
GO_TEST_NAMES = frozenset({"t", "b", "f"})
GO_TEST_TYPE = re.compile(r"\*testing\.(?:T|B|F|TB)\b")
# Directories --params does not descend into.
SKIP_DIRS = frozenset({".git", "node_modules", "target", "build", ".venv", "__pycache__"})
USAGE = "usage: style.py --params <path>..."

# Comments and string or char literals of the C-like languages, Go and TypeScript included.
NOISE = re.compile(
    "|".join(
        [
            r"//[^\n]*",
            r"/\*.*?\*/",
            r'"""[\s\S]*?"""',
            r'"(?:\\.|[^"\\\n])*"',
            r"'(?:\\.|[^'\\\n])*'",
            r"`[^`]*`",
        ]
    ),
    re.S,
)
# Rust: a quote opens a char literal only around a single character; otherwise it is a lifetime.
NOISE_RUST = re.compile(
    "|".join([r"//[^\n]*", r"/\*.*?\*/", r'"(?:\\.|[^"\\])*"', r"'(?:\\.|[^'\\\n])'"]),
    re.S,
)

IDENT = r"[A-Za-z_$][\w$]*"
# The name just before an opening parenthesis, with optional generic arguments.
NAME_BEFORE = re.compile(rf"({IDENT})\s*(?:<[^;(){{}}]*>)?\s*$")
TOKEN_BEFORE = re.compile(r"([\w$]+|[>\]])\s*$")
HEAD_SPAN = 200

TS_CONTROL = frozenset({"if", "for", "while", "switch", "catch", "with", "return", "await"})
TS_TAIL = re.compile(r"\s*(?::\s*[^{;=()\s][^{;=()]*)?(?:\{|=>)")
TS_ARROW = re.compile(r"\s*(?::[^{;=()]*)?=>")
TS_PARAM = re.compile(
    rf"\s*(?:(?:public|private|protected|readonly|override)\s+)*(?:\.\.\.)?({IDENT})\s*(?:[?:=]|$)"
)
BARE_ARROW = re.compile(rf"(?<![\w$.])({IDENT})\s*=>")
BARE_ARROW_JAVA = re.compile(r"(?<![\w$.])([A-Za-z_]\w*)\s*->")

JAVA_CONTROL = frozenset(
    {"if", "for", "while", "switch", "catch", "synchronized", "return", "new", "throw", "try"}
)
CSHARP_CONTROL = JAVA_CONTROL | frozenset(
    {"foreach", "using", "lock", "fixed", "checked", "unchecked", "typeof", "sizeof", "nameof"}
    | {"default", "when", "await"}
)
# Words that may precede a call, which makes `word name(args)` an expression, not a declaration.
NOT_A_TYPE = frozenset(
    {"return", "new", "throw", "else", "case", "assert", "yield", "await", "do", "in", "is"}
)
JAVA_TAIL = re.compile(r"\s*(?:\{|;|throws\b)")
CSHARP_TAIL = re.compile(r"\s*(?:\{|;|=>|where\b)")
JAVA_STRIP = re.compile(r"@\w+(?:\.\w+)*|\bfinal\b|\.\.\.")
CSHARP_STRIP = re.compile(r"\[[^\]]*\]|\b(?:ref|out|in|params|this|scoped|readonly)\b")
TYPED_NAME = re.compile(r"\S\s+([A-Za-z_]\w*)\s*$")
BARE_NAME = re.compile(r"\s*([A-Za-z_]\w*)\s*$")

GO_NAME = re.compile(r"\s*[A-Za-z_]\w*\s*")
GO_RECEIVER_TAIL = re.compile(r"\s*(?!func\b)[A-Za-z_]\w*\s*(?=[\[(])")
GO_ENTRY = re.compile(r"\s*([A-Za-z_]\w*)(?:\s+(\S.*))?\s*", re.S)

RUST_FN = re.compile(r"\bfn\s+[A-Za-z_]\w*\s*(?:<[^;(){}]*>)?\s*\(")
RUST_PARAM = re.compile(r"\s*(?:mut\s+)?([A-Za-z_]\w*)\s*(?::|$)")
RUST_CLOSURE_OPENERS = ("(", ",", "=", "{", ";", ":")

OPEN_BRACKETS = "([{<"
CLOSE_BRACKETS = ")]}>"

# (offset in the text, name)
Found = list[tuple[int, str]]


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    name: str
    language: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: one-letter parameter '{self.name}' ({self.language})"


@dataclass(frozen=True)
class Language:
    name: str
    # Pure: source text in, (line, name) of every one-letter parameter out.
    detect: Callable[[str], list[tuple[int, str]]]


def one_letter(name: str) -> bool:
    return len(name) == 1 and name.isascii() and name.isalpha() and name not in ALLOWED_NAMES


def blank_noise(text: str, pattern: re.Pattern[str] = NOISE) -> str:
    """Comments and literals become spaces; offsets and newlines stay."""
    return pattern.sub(lambda hit: re.sub(r"[^\n]", " ", hit.group()), text)


def paren_pairs(text: str) -> dict[int, int]:
    """Offset of every '(' mapped to the offset of its ')'."""
    pairs: dict[int, int] = {}
    stack: list[int] = []
    for pos, char in enumerate(text):
        if char == "(":
            stack.append(pos)
        elif char == ")" and stack:
            pairs[stack.pop()] = pos
    return pairs


def balanced(text: str, start: int, opener: str, closer: str) -> int:
    """Offset of the closer matching the opener at start, or -1."""
    depth = 0
    for pos in range(start, len(text)):
        if text[pos] == opener:
            depth += 1
        elif text[pos] == closer:
            depth -= 1
            if depth == 0:
                return pos
    return -1


def split_top(text: str, start: int, end: int) -> list[tuple[int, str]]:
    """Pieces of text[start:end] split on commas outside brackets, with their offsets."""
    pieces = []
    depth = 0
    begin = start
    for pos in range(start, end):
        char = text[pos]
        if char in OPEN_BRACKETS:
            depth += 1
        elif char in CLOSE_BRACKETS and not (char == ">" and text[pos - 1] in "-="):
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            pieces.append((begin, text[begin:pos]))
            begin = pos + 1
    pieces.append((begin, text[begin:end]))
    return [(offset, piece) for offset, piece in pieces if piece.strip()]


def group_pieces(blank: str, pairs: dict[int, int], open_at: int) -> list[tuple[int, str]]:
    return split_top(blank, open_at + 1, pairs[open_at])


def lines_of(text: str, found: Found) -> list[tuple[int, str]]:
    return sorted({(text.count("\n", 0, offset) + 1, name) for offset, name in found})


def head_of(blank: str, open_at: int) -> str:
    return blank[max(0, open_at - HEAD_SPAN) : open_at]


def one_letter_hits(found: Found) -> Found:
    return [(offset, name) for offset, name in found if one_letter(name)]


def declared_name(head: str, control: frozenset[str]) -> bool:
    """True when the text before a '(' ends in `Type name` (a declaration, not a call)."""
    named = NAME_BEFORE.search(head)
    if not named or named.group(1) in control:
        return False
    token = TOKEN_BEFORE.search(head[: named.start()])
    return bool(token) and token.group(1) not in NOT_A_TYPE


def blank_matches(piece: str, pattern: re.Pattern[str]) -> str:
    cut = piece.split("=")[0]
    return pattern.sub(lambda hit: " " * len(hit.group()), cut)


def typed_name(piece: str, strip: re.Pattern[str], bare: bool) -> tuple[int, str] | None:
    """The parameter name of `Type name`; with bare, a lone `name` counts too."""
    cleaned = blank_matches(piece, strip)
    hit = TYPED_NAME.search(cleaned) or (BARE_NAME.fullmatch(cleaned) if bare else None)
    return (hit.start(1), hit.group(1)) if hit else None


def declared_names(
    blank: str,
    pairs: dict[int, int],
    control: frozenset[str],
    tail: re.Pattern[str],
    strip: re.Pattern[str],
) -> Found:
    """Parameters of Java and C# methods, constructors and local functions."""
    found: Found = []
    for open_at, close_at in pairs.items():
        if not tail.match(blank, close_at + 1):
            continue
        if not declared_name(head_of(blank, open_at), control):
            continue
        for offset, piece in group_pieces(blank, pairs, open_at):
            hit = typed_name(piece, strip, bare=False)
            if hit:
                found.append((offset + hit[0], hit[1]))
    return found


def lambda_names(
    blank: str, pairs: dict[int, int], arrow: str, strip: re.Pattern[str]
) -> Found:
    """Parameters of `(a, b) ->` and `(a, b) =>` lambdas."""
    found: Found = []
    follows = re.compile(rf"\s*{re.escape(arrow)}")
    for open_at, close_at in pairs.items():
        if not follows.match(blank, close_at + 1):
            continue
        for offset, piece in group_pieces(blank, pairs, open_at):
            hit = typed_name(piece, strip, bare=True)
            if hit:
                found.append((offset + hit[0], hit[1]))
    return found


def detect_python(text: str) -> list[tuple[int, str]]:
    found = []
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        spec = node.args
        every = [*spec.posonlyargs, *spec.args, *spec.kwonlyargs, spec.vararg, spec.kwarg]
        found += [(arg.lineno, arg.arg) for arg in every if arg and one_letter(arg.arg)]
    return sorted(set(found))


def detect_typescript(text: str) -> list[tuple[int, str]]:
    blank = blank_noise(text)
    pairs = paren_pairs(blank)
    found: Found = []
    for open_at, close_at in pairs.items():
        named = NAME_BEFORE.search(head_of(blank, open_at))
        method = named and named.group(1) not in TS_CONTROL and TS_TAIL.match(blank, close_at + 1)
        if not method and not TS_ARROW.match(blank, close_at + 1):
            continue
        for offset, piece in group_pieces(blank, pairs, open_at):
            hit = TS_PARAM.match(piece)
            if hit:
                found.append((offset + hit.start(1), hit.group(1)))
    for hit in BARE_ARROW.finditer(blank):
        if not blank[: hit.start()].rstrip().endswith(":"):
            found.append((hit.start(1), hit.group(1)))
    return lines_of(text, one_letter_hits(found))


def skip_space(text: str, pos: int) -> int:
    rest = text[pos:]
    return pos + len(rest) - len(rest.lstrip())


def go_params_open(blank: str, pairs: dict[int, int], after_func: int) -> int:
    """Offset of the '(' that opens the parameters of the func at after_func, or -1."""
    pos = skip_space(blank, after_func)
    if blank.startswith("(", pos):
        close = pairs.get(pos, -1)
        receiver = GO_RECEIVER_TAIL.match(blank, close + 1) if close >= 0 else None
        if not receiver:
            return pos
        pos = receiver.end()
    else:
        name = GO_NAME.match(blank, pos)
        if not name:
            return -1
        pos = name.end()
    if blank.startswith("[", pos):
        end = balanced(blank, pos, "[", "]")
        if end < 0:
            return -1
        pos = skip_space(blank, end + 1)
    return pos if blank.startswith("(", pos) else -1


def go_entries(blank: str, pairs: dict[int, int], open_at: int) -> list[tuple[int, str, str]]:
    """(offset, name, type) per parameter name; empty for a list of types only."""
    entries = []
    for offset, piece in group_pieces(blank, pairs, open_at):
        hit = GO_ENTRY.fullmatch(piece)
        if hit:
            entries.append((offset + hit.start(1), hit.group(1), hit.group(2)))
    if not any(kind for _, _, kind in entries):
        return []
    named = []
    kind = ""
    for offset, name, own in reversed(entries):
        kind = own or kind
        named.append((offset, name, kind))
    return named[::-1]


def detect_go(text: str) -> list[tuple[int, str]]:
    blank = blank_noise(text)
    pairs = paren_pairs(blank)
    found: Found = []
    for func in re.finditer(r"\bfunc\b", blank):
        open_at = go_params_open(blank, pairs, func.end())
        if open_at < 0 or open_at not in pairs:
            continue
        for offset, name, kind in go_entries(blank, pairs, open_at):
            if name in GO_TEST_NAMES and GO_TEST_TYPE.match(kind):
                continue
            found.append((offset, name))
    return lines_of(text, one_letter_hits(found))


def rust_closures(blank: str) -> Found:
    found: Found = []
    for bar in re.finditer(r"\|", blank):
        at = bar.start()
        if blank[at + 1 : at + 2] == "|" or blank[at - 1 : at] == "|":
            continue
        before = blank[max(0, at - 20) : at].rstrip()
        if not (before.endswith(RUST_CLOSURE_OPENERS) or re.search(r"\bmove$", before)):
            continue
        end = blank.find("|", at + 1)
        if end < 0:
            continue
        for offset, piece in split_top(blank, at + 1, end):
            hit = RUST_PARAM.match(piece)
            if hit:
                found.append((offset + hit.start(1), hit.group(1)))
    return found


def detect_rust(text: str) -> list[tuple[int, str]]:
    blank = blank_noise(text, NOISE_RUST)
    pairs = paren_pairs(blank)
    found = rust_closures(blank)
    for fn in RUST_FN.finditer(blank):
        for offset, piece in group_pieces(blank, pairs, fn.end() - 1):
            hit = RUST_PARAM.match(piece)
            if hit:
                found.append((offset + hit.start(1), hit.group(1)))
    return lines_of(text, one_letter_hits(found))


def detect_java(text: str) -> list[tuple[int, str]]:
    blank = blank_noise(text)
    pairs = paren_pairs(blank)
    found = declared_names(blank, pairs, JAVA_CONTROL, JAVA_TAIL, JAVA_STRIP)
    found += lambda_names(blank, pairs, "->", JAVA_STRIP)
    for hit in BARE_ARROW_JAVA.finditer(blank):
        if not re.search(r"\bcase\s+$", blank[max(0, hit.start() - 20) : hit.start()]):
            found.append((hit.start(1), hit.group(1)))
    return lines_of(text, one_letter_hits(found))


def detect_csharp(text: str) -> list[tuple[int, str]]:
    blank = blank_noise(text)
    pairs = paren_pairs(blank)
    found = declared_names(blank, pairs, CSHARP_CONTROL, CSHARP_TAIL, CSHARP_STRIP)
    found += lambda_names(blank, pairs, "=>", CSHARP_STRIP)
    for hit in BARE_ARROW.finditer(blank):
        # `string s =>` is a pattern binding, not a lambda parameter.
        word = TOKEN_BEFORE.search(blank[: hit.start()])
        if not word or word.group(1) in {"async", "static"} or not word.group(1)[0].isalpha():
            found.append((hit.start(1), hit.group(1)))
    return lines_of(text, one_letter_hits(found))


LANGUAGES: dict[str, Language] = {
    ".py": Language("python", detect_python),
    ".ts": Language("typescript", detect_typescript),
    ".go": Language("go", detect_go),
    ".rs": Language("rust", detect_rust),
    ".java": Language("java", detect_java),
    ".cs": Language("csharp", detect_csharp),
}


def tracked_sources() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split("\n")
    return [Path(p) for p in out if Path(p).suffix in SOURCE and Path(p).exists()]


def trailing_comment(line: str, marker: str) -> bool:
    """True when code precedes a line comment on the same line."""
    code = STRING.sub('""', line)
    head, sep, _ = code.partition(marker)
    return bool(sep) and bool(head.strip()) and not head.rstrip().endswith(marker[0])


def param_files(roots: list[str]) -> list[Path]:
    files = []
    for root in map(Path, roots):
        if root.is_dir():
            files += [
                path
                for path in root.rglob("*")
                if path.is_file() and not SKIP_DIRS & set(path.relative_to(root).parts)
            ]
        else:
            files.append(root)
    return sorted(path for path in files if path.suffix in LANGUAGES)


def check_params(roots: list[str]) -> list[tuple[str, int, str]]:
    """(path, line, message) of every problem found, unsorted."""
    problems = []
    for path in param_files(roots):
        language = LANGUAGES[path.suffix]
        try:
            hits = language.detect(path.read_text())
        except (SyntaxError, ValueError, UnicodeDecodeError) as err:
            problems.append((str(path), 0, f"{path}: cannot parse ({err})"))
            continue
        for line, name in hits:
            violation = Violation(path, line, name, language.name)
            problems.append((str(path), line, str(violation)))
    return problems


def wants_params(argv: list[str]) -> bool:
    return len(argv) > 1 and argv[1] == "--params"


def params_main(roots: list[str]) -> int:
    if not roots:
        print(USAGE, file=sys.stderr)
        return 2
    problems = sorted(check_params(roots))
    print("\n".join(message for _, _, message in problems) or "params ok")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    if wants_params(argv):
        return params_main(argv[2:])
    sources = tracked_sources()
    problems = []
    for path in sources:
        marker = LINE_COMMENT.get(path.suffix, "//")
        for no, line in enumerate(path.read_text().splitlines(), 1):
            if len(line.expandtabs(4)) > MAX_COLS:
                problems.append(f"{path}:{no}: longer than {MAX_COLS} columns")
            if not line.isascii():
                problems.append(f"{path}:{no}: non-ASCII character")
            if trailing_comment(line, marker) and "http" not in line:
                problems.append(f"{path}:{no}: trailing comment; put it on the line above")
    # Tracked files only: submodules and generated directories are other code.
    problems += [message for _, _, message in sorted(check_params([str(p) for p in sources]))]
    print("\n".join(problems) or "style ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
