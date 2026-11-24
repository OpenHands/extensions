#!/usr/bin/env python3
"""Fail if any plugin ships non-source noise in its SDK-visible resource dirs.

The OpenHands SDK's skill loader (`openhands.sdk.skills`) walks a fixed set of
directory names under each plugin and lists everything it finds in that plugin's
`SkillResources` manifest:

    >>> from openhands.sdk.skills import RESOURCE_DIRECTORIES
    >>> RESOURCE_DIRECTORIES
    ('scripts', 'references', 'assets')

Anything that lands in one of those directories becomes visible to the agent at
skill-load time. A stale ``__pycache__/warm_runtime_configs.cpython-313.pyc``
left behind by a developer running tests in-tree therefore gets surfaced to
every downstream consumer that loads the plugin as a skill.

This check scans ``plugins/<name>/{scripts,references,assets}`` for files that
clearly aren't skill content - Python bytecode caches, pytest caches, editor
backups, OS litter - and exits 1 if any are found. Keep this list narrow: it
should flag obvious noise, not police plugin contents.

Usage:
    python scripts/check_plugin_resources.py            # scan and report
    python scripts/check_plugin_resources.py --fix      # also delete offenders
"""

from __future__ import annotations

import argparse
import fnmatch
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"

# Mirrors openhands.sdk.skills.RESOURCE_DIRECTORIES. Pinned here rather than
# imported so the check runs without the SDK installed in CI.
RESOURCE_DIRECTORIES = ("scripts", "references", "assets")

# Names (dirs or files) that should never appear under a resource directory.
# Dir patterns match against directory basenames; file patterns are fnmatch'd
# against file basenames.
_FORBIDDEN_DIR_NAMES = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})
_FORBIDDEN_FILE_GLOBS = ("*.pyc", "*.pyo", "*.pyd", "*.swp", "*.swo", ".DS_Store", "Thumbs.db")


def _is_forbidden_file(name: str) -> bool:
    return any(fnmatch.fnmatchcase(name, pat) for pat in _FORBIDDEN_FILE_GLOBS)


def scan() -> list[Path]:
    offenders: list[Path] = []
    if not PLUGINS_DIR.is_dir():
        return offenders
    for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
        if not plugin_dir.is_dir():
            continue
        for resource_name in RESOURCE_DIRECTORIES:
            resource_dir = plugin_dir / resource_name
            if not resource_dir.is_dir():
                continue
            for path in sorted(resource_dir.rglob("*")):
                if path.is_dir() and path.name in _FORBIDDEN_DIR_NAMES:
                    offenders.append(path)
                elif path.is_file() and _is_forbidden_file(path.name):
                    offenders.append(path)
    return offenders


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Delete offending files/dirs instead of just failing.",
    )
    args = parser.parse_args()

    offenders = scan()
    if not offenders:
        print(f"OK: no non-source files found under plugins/*/{{{','.join(RESOURCE_DIRECTORIES)}}}/")
        return 0

    print(
        f"ERROR: {len(offenders)} non-source entries found under plugin resource "
        f"directories. These would be surfaced to agents in SkillResources:",
        file=sys.stderr,
    )
    for path in offenders:
        kind = "dir " if path.is_dir() else "file"
        print(f"  {kind}  {path.relative_to(REPO_ROOT)}", file=sys.stderr)

    if args.fix:
        # Delete deepest paths first so a child file inside a to-be-removed
        # __pycache__ directory doesn't vanish out from under its own unlink.
        for path in sorted(offenders, key=lambda p: len(p.parts), reverse=True):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
        print(f"\nRemoved {len(offenders)} entries.", file=sys.stderr)
        return 0

    print(
        "\nRe-run with --fix to delete, or add the pattern to .gitignore and "
        "clean your working tree. These are typically produced by running tests "
        "in-tree without PYTHONDONTWRITEBYTECODE=1.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
