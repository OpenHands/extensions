#!/usr/bin/env python3
"""Static analysis for deprecation deadlines.

This is the OpenHands SDK deprecation checker, scoped to the extensions
package. It scans the SDK's three supported mechanisms: ``@deprecated``,
``warn_deprecated``, and ``warn_cleanup``. The only policy difference is the
two-minor-release runway used by extensions.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from packaging import version as pkg_version


# This is intentionally shorter than the SDK's five-release policy: the public
# extensions API removes deprecated raw catalog helpers after two minor releases.
DEPRECATION_RUNWAY_MINOR_RELEASES = 2
REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class PackageConfig:
    name: str
    pyproject: Path
    source_roots: tuple[Path, ...]


PACKAGES: tuple[PackageConfig, ...] = (
    PackageConfig(
        name="openhands-extensions",
        pyproject=REPO_ROOT / "pyproject.toml",
        source_roots=(REPO_ROOT / "python" / "openhands_extensions",),
    ),
)


@dataclass(slots=True)
class DeprecationRecord:
    identifier: str
    removed_in: str | date | None
    deprecated_in: str | None
    path: Path
    line: int
    kind: Literal["decorator", "warn_call", "cleanup_call"]
    package: str


def _load_current_version(pyproject: Path) -> str:
    data = tomllib.loads(pyproject.read_text())
    try:
        return str(data["project"]["version"])
    except KeyError as exc:  # pragma: no cover - configuration error
        raise SystemExit(
            f"Unable to determine project version from {pyproject}"
        ) from exc


def _iter_python_files(root: Path) -> Iterator[Path]:
    for path in root.rglob("*.py"):
        if path.name == "__init__.py" and path.parent == root:
            continue
        yield path


def _parse_removed_value(
    node: ast.AST | None,
    *,
    path: Path,
    line: int,
) -> str | date | None:
    if node is None:
        return None

    expression = ast.unparse(node)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value
        if node.value is None:
            return None
        raise SystemExit(
            f"Unsupported removed_in literal at {path}:{line}: {expression}"
        )

    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name) and func.id == "date":
            try:
                args = [_safe_int_literal(arg) for arg in node.args]
                kwargs = {
                    kw.arg: _safe_int_literal(kw.value)
                    for kw in node.keywords
                    if kw.arg is not None
                }
            except ValueError as exc:
                raise SystemExit(
                    f"Unsupported removed_in date() arguments at {path}:{line}:"
                    f" {expression}"
                ) from exc

            if any(kw.arg is None for kw in node.keywords):
                raise SystemExit(
                    "Unsupported removed_in date() call (uses **kwargs) at "
                    f"{path}:{line}: {expression}"
                )

            try:
                return date(*args, **kwargs)
            except TypeError as exc:
                raise SystemExit(
                    f"Invalid removed_in date() call at {path}:{line}: {expression}"
                ) from exc

        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "date"
            and func.attr == "today"
        ):
            if node.args or node.keywords:
                raise SystemExit(
                    "date.today() removed_in call must not include arguments at "
                    f"{path}:{line}: {expression}"
                )
            return date.today()

    raise SystemExit(
        f"Unsupported removed_in expression at {path}:{line}: {expression}"
    )


def _parse_deprecated_value(
    node: ast.AST | None,
    *,
    path: Path,
    line: int,
) -> str | None:
    if node is None:
        return None

    expression = ast.unparse(node)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value
        if node.value is None:
            return None

    raise SystemExit(
        f"Unsupported deprecated_in expression at {path}:{line}: {expression}"
    )


def _safe_int_literal(node: ast.AST) -> int:
    if not isinstance(node, ast.Constant) or not isinstance(node.value, int):
        raise ValueError(
            f"Unsupported expression inside literal evaluation: {ast.unparse(node)}"
        )
    return node.value


def _extract_kw(call: ast.Call, name: str) -> ast.AST | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _gather_decorators(
    tree: ast.AST, path: Path, *, package: str
) -> Iterator[DeprecationRecord]:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue

        for deco in node.decorator_list:
            call = deco if isinstance(deco, ast.Call) else None
            if call is None:
                continue

            target = call.func
            if isinstance(target, ast.Name):
                decorator_name = target.id
            elif isinstance(target, ast.Attribute):
                decorator_name = target.attr
            else:
                continue

            if decorator_name != "deprecated":
                continue

            removed_expr = _extract_kw(call, "removed_in")
            deprecated_expr = _extract_kw(call, "deprecated_in")

            yield DeprecationRecord(
                identifier=_build_identifier(node),
                removed_in=_parse_removed_value(
                    removed_expr, path=path, line=node.lineno
                ),
                deprecated_in=_parse_deprecated_value(
                    deprecated_expr, path=path, line=node.lineno
                ),
                path=path,
                line=node.lineno,
                kind="decorator",
                package=package,
            )


def _gather_warn_calls(
    tree: ast.AST, path: Path, *, package: str
) -> Iterator[DeprecationRecord]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        target = node.func
        if isinstance(target, ast.Name):
            func_name = target.id
        elif isinstance(target, ast.Attribute):
            func_name = target.attr
        else:
            continue

        if func_name == "warn_deprecated":
            identifier_node = node.args[0] if node.args else None
            if identifier_node is None:
                continue
            identifier = ast.unparse(identifier_node)

            removed_expr = _extract_kw(node, "removed_in")
            deprecated_expr = _extract_kw(node, "deprecated_in")

            yield DeprecationRecord(
                identifier=identifier,
                removed_in=_parse_removed_value(
                    removed_expr, path=path, line=node.lineno
                ),
                deprecated_in=_parse_deprecated_value(
                    deprecated_expr, path=path, line=node.lineno
                ),
                path=path,
                line=node.lineno,
                kind="warn_call",
                package=package,
            )
        elif func_name == "warn_cleanup":
            identifier_node = node.args[0] if node.args else None
            if identifier_node is None:
                continue
            identifier = ast.unparse(identifier_node)

            cleanup_expr = _extract_kw(node, "cleanup_by")

            yield DeprecationRecord(
                identifier=identifier,
                removed_in=_parse_removed_value(
                    cleanup_expr, path=path, line=node.lineno
                ),
                deprecated_in=None,
                path=path,
                line=node.lineno,
                kind="cleanup_call",
                package=package,
            )


def _build_identifier(node: ast.AST) -> str:
    if isinstance(node, ast.ClassDef):
        return node.name
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        qual_name = node.name
        if node.decorator_list:
            parent = getattr(node, "parent", None)
            if parent and isinstance(parent, ast.ClassDef):
                return f"{parent.name}.{node.name}"
        return qual_name
    return "<unknown>"


def _attach_parents(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            setattr(child, "parent", node)


def _collect_records(files: Iterable[Path], *, package: str) -> list[DeprecationRecord]:
    records: list[DeprecationRecord] = []
    for path in files:
        tree = ast.parse(path.read_text())
        _attach_parents(tree)
        records.extend(_gather_decorators(tree, path, package=package))
        records.extend(_gather_warn_calls(tree, path, package=package))
    return records


def _version_ge(current: str, target: str) -> bool:
    try:
        return pkg_version.parse(current) >= pkg_version.parse(target)
    except pkg_version.InvalidVersion as exc:
        raise SystemExit(
            f"Invalid semantic version comparison: {current=} {target=}"
        ) from exc


def _minimum_removed_in(deprecated_in: str) -> str:
    parsed = pkg_version.parse(deprecated_in)
    if not isinstance(parsed, pkg_version.Version):
        raise SystemExit(f"Invalid deprecated_in version: {deprecated_in!r}")
    return f"{parsed.major}.{parsed.minor + DEPRECATION_RUNWAY_MINOR_RELEASES}.0"


def _runway_error(record: DeprecationRecord) -> str | None:
    if record.kind == "cleanup_call" or record.removed_in is None:
        return None
    if isinstance(record.removed_in, date):
        return None
    if record.deprecated_in is None:
        return (
            f"{record.identifier} does not declare deprecated_in; version-based "
            "deprecations must provide an explicit runway."
        )

    try:
        minimum_removed_in = _minimum_removed_in(record.deprecated_in)
        if pkg_version.parse(str(record.removed_in)) >= pkg_version.parse(
            minimum_removed_in
        ):
            return None
    except pkg_version.InvalidVersion as exc:
        raise SystemExit(
            f"Invalid deprecation schedule at {record.path}:{record.line}: "
            f"deprecated_in={record.deprecated_in!r}, "
            f"removed_in={record.removed_in!r}"
        ) from exc

    return (
        f"{record.identifier} uses an invalid deprecation schedule: "
        f"deprecated_in={record.deprecated_in} and "
        f"removed_in={record.removed_in}. Deprecations require at least "
        f"{DEPRECATION_RUNWAY_MINOR_RELEASES} minor releases of runway "
        f"(minimum removed_in: {minimum_removed_in})."
    )


def _should_fail(current_version: str, record: DeprecationRecord) -> bool:
    removed = record.removed_in
    if removed is None:
        return False
    if isinstance(removed, date):
        return date.today() >= removed
    try:
        return _version_ge(current_version, str(removed))
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - unexpected literal type
        raise SystemExit(
            f"Unsupported removed_in expression in {record.path}:{record.line}:"
            f" {removed!r}"
        ) from exc


def _format_record(record: DeprecationRecord) -> str:
    location = record.path.relative_to(REPO_ROOT)
    removed = record.removed_in if record.removed_in is not None else "(none)"

    if record.kind == "cleanup_call":
        return (
            f"- [{record.package}] {record.identifier} ({record.kind})\n"
            f"  cleanup by:    {removed}\n"
            f"  defined at:    {location}:{record.line}"
        )

    deprecated = (
        record.deprecated_in if record.deprecated_in is not None else "(unknown)"
    )
    return (
        f"- [{record.package}] {record.identifier} ({record.kind})\n"
        f"  deprecated in: {deprecated}\n"
        f"  removed in:    {removed}\n"
        f"  defined at:    {location}:{record.line}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    del argv  # The SDK checker takes no command-line configuration.

    overdue: list[DeprecationRecord] = []
    invalid_runway: list[tuple[DeprecationRecord, str]] = []
    total_records = 0
    package_summaries: list[tuple[str, str, int]] = []

    for package in PACKAGES:
        if not package.pyproject.exists():
            raise SystemExit(
                f"Unable to locate pyproject.toml for {package.name}: "
                f"{package.pyproject}"
            )

        current_version = _load_current_version(package.pyproject)

        files: list[Path] = []
        for root in package.source_roots:
            if not root.exists():
                raise SystemExit(
                    f"Source root {root} for package {package.name} does not exist"
                )
            files.extend(_iter_python_files(root))

        records = _collect_records(files, package=package.name)
        overdue.extend(r for r in records if _should_fail(current_version, r))
        invalid_runway.extend(
            (record, error)
            for record in records
            if (error := _runway_error(record)) is not None
        )
        total_records += len(records)
        package_summaries.append((package.name, current_version, len(records)))

    if overdue or invalid_runway:
        deprecated_items = [r for r in overdue if r.kind != "cleanup_call"]
        cleanup_items = [r for r in overdue if r.kind == "cleanup_call"]

        if invalid_runway:
            print(
                "The following deprecation schedules provide less than "
                f"{DEPRECATION_RUNWAY_MINOR_RELEASES} minor releases of runway:\n"
            )
            for record, error in invalid_runway:
                print(_format_record(record))
                print(f"  error:         {error}")
                print()

        if deprecated_items:
            print(
                "The following deprecated features have passed their removal "
                "deadline:\n"
            )
            for record in deprecated_items:
                print(_format_record(record))
                print()

        if cleanup_items:
            print("The following workarounds have passed their cleanup deadline:\n")
            for record in cleanup_items:
                print(_format_record(record))
                print()

        if deprecated_items:
            print(
                "Update or remove the listed features before publishing a version that "
                "meets or exceeds their removal deadline."
            )
        if cleanup_items:
            print(
                "Remove the listed workarounds before publishing a version that "
                "meets or exceeds their cleanup deadline."
            )
        if invalid_runway:
            print(
                "Move each removal target far enough out, or remove the invalid "
                "deprecation metadata before merging."
            )
        return 1

    for package_name, version, count in package_summaries:
        print(
            f"{package_name}: checked {count} deprecation metadata entries against "
            f"version {version}."
        )
    print(
        f"Checked {total_records} deprecation metadata entries across "
        f"{len(package_summaries)} package(s)."
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation
    sys.exit(main(sys.argv[1:]))
