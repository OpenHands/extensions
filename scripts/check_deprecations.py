#!/usr/bin/env python3
"""Enforce versioned deprecation deadlines for public Python bindings.

The check mirrors the OpenHands SDK's deprecation-deadline policy.  It scans
``@deprecated(...)`` declarations, verifies a two-minor-release runway, and
fails when the package version reaches a feature's ``removed_in`` version.  It
therefore turns red on the release-please PR that would otherwise publish a
release with an overdue compatibility shim still present.
"""

from __future__ import annotations

import argparse
import ast
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from packaging.version import InvalidVersion, Version


DEPRECATION_RUNWAY_MINOR_RELEASES = 2
REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = REPO_ROOT / "python" / "openhands_extensions"


@dataclass(frozen=True)
class DeprecationRecord:
    identifier: str
    deprecated_in: str
    removed_in: str
    path: Path
    line: int


def _current_version() -> str:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def _literal_keyword(call: ast.Call, name: str, path: Path) -> str:
    value = next((kw.value for kw in call.keywords if kw.arg == name), None)
    if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
        raise SystemExit(
            f"{path}:{call.lineno}: deprecated() requires a string {name} argument"
        )
    return value.value


def _decorator_call(node: ast.AST) -> ast.Call | None:
    if not isinstance(node, ast.Call):
        return None
    if isinstance(node.func, ast.Name) and node.func.id == "deprecated":
        return node
    if isinstance(node.func, ast.Attribute) and node.func.attr == "deprecated":
        return node
    return None


def _records() -> list[DeprecationRecord]:
    records: list[DeprecationRecord] = []
    for path in PYTHON_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for decorator in node.decorator_list:
                call = _decorator_call(decorator)
                if call is None:
                    continue
                records.append(
                    DeprecationRecord(
                        identifier=node.name,
                        deprecated_in=_literal_keyword(call, "deprecated_in", path),
                        removed_in=_literal_keyword(call, "removed_in", path),
                        path=path,
                        line=node.lineno,
                    )
                )
    return records


def _minimum_removal_version(deprecated_in: str) -> Version:
    try:
        version = Version(deprecated_in)
    except InvalidVersion as exc:
        raise SystemExit(f"Invalid deprecated_in version: {deprecated_in!r}") from exc
    return Version(
        f"{version.major}.{version.minor + DEPRECATION_RUNWAY_MINOR_RELEASES}.0"
    )


def _errors(current_version: str, records: list[DeprecationRecord]) -> list[str]:
    try:
        current = Version(current_version)
    except InvalidVersion as exc:
        raise SystemExit(f"Invalid project version: {current_version!r}") from exc

    errors: list[str] = []
    for record in records:
        try:
            removed = Version(record.removed_in)
        except InvalidVersion as exc:
            raise SystemExit(
                f"Invalid removed_in version at {record.path}:{record.line}: "
                f"{record.removed_in!r}"
            ) from exc
        minimum = _minimum_removal_version(record.deprecated_in)
        location = record.path.relative_to(REPO_ROOT)
        if removed < minimum:
            errors.append(
                f"{location}:{record.line}: {record.identifier} has insufficient "
                f"deprecation runway ({record.deprecated_in} -> {record.removed_in}; "
                f"minimum removal version is {minimum})."
            )
        if current >= removed:
            errors.append(
                f"{location}:{record.line}: {record.identifier} reached its removal "
                f"version {record.removed_in} (current version: {current_version}); "
                "remove the deprecated compatibility API before releasing."
            )
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--current-version",
        help="Override the package version (used to test release-please deadlines).",
    )
    args = parser.parse_args(argv)

    records = _records()
    errors = _errors(args.current_version or _current_version(), records)
    if errors:
        print("Deprecation deadline check failed:")
        print(*[f"- {error}" for error in errors], sep="\n")
        return 1

    print(f"Checked {len(records)} deprecation entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
