#!/usr/bin/env python3
"""Fail if any uncommitted change to a code file touches something other than comments.

Run from inside the target repository after editing and before committing. Compares
each modified file against HEAD:
  - Python: the ASTs must be identical, which also proves docstrings are untouched.
  - Other languages: the code left after a string-aware comment strip must match.
README and other prose files are listed for manual diff review but not checked.

Exit status is 1 when any file fails; revert those files (`git checkout -- <path>`)
or fix them and re-run.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comment_syntax import PYTHON, kind_for, scan, syntax_for  # noqa: E402


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-c", "core.quotePath=false", *args], capture_output=True, text=True, check=True
    ).stdout


def python_unchanged(before: str, after: str) -> bool | None:
    try:
        return ast.dump(ast.parse(before)) == ast.dump(ast.parse(after))
    except SyntaxError:
        return None


def check(path: str) -> str | None:
    before = git("show", f"HEAD:{path}")
    after = Path(path).read_text()
    syn = syntax_for(path)
    if syn is PYTHON:
        same = python_unchanged(before, after)
        if same is not None:
            return None if same else "Python AST changed (code or docstring edited)"
    before_code, _ = scan(before, syn)
    after_code, _ = scan(after, syn)
    if before_code == after_code:
        return None
    for b, a in zip(before_code, after_code, strict=False):
        if b != a:
            return f"code changed: {b.strip()!r} -> {a.strip()!r}"
    return f"code line count changed ({len(before_code)} -> {len(after_code)})"


def main() -> int:
    changed = [p for p in git("diff", "--name-only", "HEAD").splitlines() if p]
    untracked = [p for p in git("ls-files", "--others", "--exclude-standard").splitlines() if p]
    failures, prose = [], []
    for path in untracked:
        print(f"NOTE    {path} is untracked; do not commit it as part of the cleanup")
    for path in changed:
        if not Path(path).exists():
            failures.append((path, "file deleted"))
            continue
        kind = kind_for(path)
        if kind == "code":
            problem = check(path)
            if problem:
                failures.append((path, problem))
        elif kind == "readme":
            prose.append(path)
        else:
            failures.append((path, "not a code or README file"))

    for path in prose:
        print(f"REVIEW  {path} (prose: check the diff by hand)")
    for path, problem in failures:
        print(f"FAIL    {path}: {problem}")
    ok = len(changed) - len(prose) - sum(1 for p, _ in failures if p in changed)
    print(f"{ok} code files verified comment-only, {len(prose)} prose files to review, {len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
