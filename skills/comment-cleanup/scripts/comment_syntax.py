"""Comment syntax table and a string-aware comment stripper shared by the cleanup scripts."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True)
class Syntax:
    line: tuple[str, ...] = ()
    block: tuple[tuple[str, str], ...] = ()
    quotes: tuple[str, ...] = ('"', "'")
    multiline_quotes: tuple[str, ...] = ()
    # Shell-like languages: `$#` and `${#x}` are code, so `#` only opens a comment after whitespace.
    hash_needs_space: bool = False


PYTHON = Syntax(line=("#",), multiline_quotes=('"""', "'''"))
HASH = Syntax(line=("#",), hash_needs_space=True)
C_LIKE = Syntax(line=("//",), block=(("/*", "*/"),), multiline_quotes=("`",))
CSS = Syntax(block=(("/*", "*/"),))
SQL = Syntax(line=("--",), block=(("/*", "*/"),))
DASH = Syntax(line=("--",))
HTML = Syntax(block=(("<!--", "-->"),))
WEB_COMPONENT = Syntax(line=("//",), block=(("<!--", "-->"), ("/*", "*/")), multiline_quotes=("`",))
PHP = Syntax(line=("//", "#"), block=(("/*", "*/"),), hash_needs_space=True)

EXTENSIONS: dict[str, Syntax] = {
    ".py": PYTHON, ".pyi": PYTHON,
    **dict.fromkeys(
        [".sh", ".bash", ".zsh", ".rb", ".pl", ".r", ".yaml", ".yml", ".toml", ".tf", ".hcl",
         ".ps1", ".nix", ".ex", ".exs", ".jl", ".mk", ".cmake"],
        HASH,
    ),
    **dict.fromkeys(
        [".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".java", ".kt", ".kts",
         ".scala", ".go", ".rs", ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".cs", ".swift",
         ".dart", ".groovy", ".gradle", ".proto", ".sol", ".zig", ".scss", ".less"],
        C_LIKE,
    ),
    ".css": CSS,
    ".sql": SQL,
    ".lua": DASH, ".hs": DASH, ".elm": DASH,
    ".html": HTML, ".htm": HTML,
    ".vue": WEB_COMPONENT, ".svelte": WEB_COMPONENT,
    ".php": PHP,
}

FILENAMES: dict[str, Syntax] = {
    "Dockerfile": HASH, "Makefile": HASH, "GNUmakefile": HASH, "CMakeLists.txt": HASH,
    "Gemfile": HASH, "Rakefile": HASH, "Vagrantfile": HASH, "Jenkinsfile": C_LIKE,
}

README_SUFFIXES = {"", ".md", ".markdown", ".rst", ".txt", ".adoc"}

DEFAULT_EXCLUDED_DIRS = {
    "node_modules", "vendor", "third_party", "third-party", "dist", "build", "out", "target",
    ".venv", "venv", "__pycache__", "coverage", "migrations", "bower_components",
    "site-packages", ".next", ".nuxt", ".yarn",
}

DEFAULT_EXCLUDED_FILES = [
    "*.min.js", "*.min.css", "*.bundle.js", "*_pb2.py", "*_pb2_grpc.py", "*.pb.go",
    "*.generated.*", "*.g.dart", "*.freezed.dart",
]


def is_readme(path: str) -> bool:
    p = PurePosixPath(path)
    return p.name.upper().startswith("README") and p.suffix.lower() in README_SUFFIXES


def syntax_for(path: str) -> Syntax | None:
    p = PurePosixPath(path)
    if p.name in FILENAMES:
        return FILENAMES[p.name]
    if p.name.startswith("Dockerfile"):
        return HASH
    return EXTENSIONS.get(p.suffix.lower())


def kind_for(path: str) -> str | None:
    if is_readme(path):
        return "readme"
    if syntax_for(path) is not None:
        return "code"
    return None


def is_default_excluded(path: str) -> bool:
    parts = PurePosixPath(path).parts
    if any(part in DEFAULT_EXCLUDED_DIRS for part in parts[:-1]):
        return True
    return any(fnmatch.fnmatch(parts[-1], pat) for pat in DEFAULT_EXCLUDED_FILES)


def _normalize(line: str) -> str:
    stripped = line.lstrip()
    indent = line[: len(line) - len(stripped)]
    return indent + " ".join(stripped.split())


def scan(text: str, syn: Syntax) -> tuple[list[str], int]:
    """Return (non-blank code lines with comments removed, number of comments seen)."""
    lines: list[str] = []
    cur: list[str] = []
    comments = 0
    in_block: str | None = None
    in_str: str | None = None
    quotes = syn.multiline_quotes + syn.quotes
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            # Unterminated single-line strings end at EOL so a stray apostrophe can't swallow the file.
            if in_str and in_str not in syn.multiline_quotes:
                in_str = None
            lines.append("".join(cur))
            cur = []
            i += 1
            continue
        if in_block:
            if text.startswith(in_block, i):
                i += len(in_block)
                in_block = None
            else:
                i += 1
            continue
        if in_str:
            if ch == "\\":
                cur.append(text[i : i + 2])
                i += 2
            elif text.startswith(in_str, i):
                cur.append(in_str)
                i += len(in_str)
                in_str = None
            else:
                cur.append(ch)
                i += 1
            continue

        opened = next((pair for pair in syn.block if text.startswith(pair[0], i)), None)
        if opened:
            comments += 1
            in_block = opened[1]
            i += len(opened[0])
            continue
        marker = next((m for m in syn.line if text.startswith(m, i)), None)
        if marker and not (marker == "#" and syn.hash_needs_space and i > 0 and not text[i - 1].isspace()):
            if not (i == 0 and text.startswith("#!")):
                comments += 1
            end = text.find("\n", i)
            i = n if end == -1 else end
            continue
        quote = next((q for q in quotes if text.startswith(q, i)), None)
        if quote:
            in_str = quote
            cur.append(quote)
            i += len(quote)
            continue
        cur.append(ch)
        i += 1
    lines.append("".join(cur))
    return [_normalize(line) for line in lines if line.strip()], comments
