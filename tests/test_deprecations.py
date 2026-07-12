"""Tests for the SDK-aligned public deprecation policy."""

from __future__ import annotations

import ast
import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from deprecation import DeprecatedWarning, UnsupportedWarning

from openhands_extensions.deprecation import (
    deprecated,
    handle_deprecated_model_fields,
    warn_cleanup,
    warn_deprecated,
)


ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "check_deprecations.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("extensions_deprecation_check", CHECK)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_deprecated_decorator_warns_and_preserves_calls() -> None:
    @deprecated(
        deprecated_in="0.10.0",
        removed_in="0.12.0",
        current_version="0.10.0",
        details="Use replacement().",
    )
    def legacy(value: int) -> int:
        return value * 2

    with pytest.warns(DeprecatedWarning, match="legacy"):
        assert legacy(3) == 6


def test_dynamic_deprecation_warnings_match_the_sdk() -> None:
    with pytest.warns(DeprecatedWarning, match="dynamic legacy API"):
        warn_deprecated(
            "dynamic legacy API",
            deprecated_in="0.10.0",
            removed_in="0.12.0",
            current_version="0.10.0",
        )

    with pytest.warns(UnsupportedWarning, match="dynamic legacy API"):
        warn_deprecated(
            "dynamic legacy API",
            deprecated_in="0.10.0",
            removed_in="0.12.0",
            current_version="0.12.0",
        )


def test_cleanup_warning_and_model_field_compatibility_match_the_sdk() -> None:
    with pytest.warns(UserWarning, match="Cleanup required: temporary workaround"):
        warn_cleanup(
            "temporary workaround",
            cleanup_by="0.12.0",
            current_version="0.12.0",
        )

    data = {"current": "value", "legacy": "old"}
    assert handle_deprecated_model_fields(data, ("legacy",)) == {"current": "value"}
    assert (
        handle_deprecated_model_fields("not a mapping", ("legacy",)) == "not a mapping"
    )


def test_checker_scans_all_sdk_deprecation_mechanisms() -> None:
    checker = _load_checker()
    tree = ast.parse(
        """
@deprecated(deprecated_in=\"0.10.0\", removed_in=\"0.12.0\")
def decorated(): pass

warn_deprecated(\"dynamic API\", deprecated_in=\"0.10.0\", removed_in=\"0.12.0\")
warn_cleanup(\"temporary workaround\", cleanup_by=date(2030, 1, 1))
"""
    )

    records = [
        *checker._gather_decorators(tree, CHECK, package="openhands-extensions"),
        *checker._gather_warn_calls(tree, CHECK, package="openhands-extensions"),
    ]

    assert [(record.identifier, record.kind) for record in records] == [
        ("decorated", "decorator"),
        ("'dynamic API'", "warn_call"),
        ("'temporary workaround'", "cleanup_call"),
    ]
    assert records[2].removed_in == date(2030, 1, 1)


def test_release_please_deadline_passes_before_removal_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checker = _load_checker()
    monkeypatch.setattr(checker, "_load_current_version", lambda _: "0.10.0")

    assert checker.main() == 0


def test_release_please_deadline_fails_at_removal_version(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checker = _load_checker()
    monkeypatch.setattr(checker, "_load_current_version", lambda _: "0.12.0")

    assert checker.main() == 1
    output = capsys.readouterr().out
    assert "list_integration_catalog" in output
    assert "get_integration_catalog_entry" in output


def test_date_based_deadlines_use_the_sdk_semantics() -> None:
    with pytest.warns(DeprecatedWarning, match="scheduled dynamic API"):
        warn_deprecated(
            "scheduled dynamic API",
            deprecated_in="0.10.0",
            removed_in=date.today() + timedelta(days=1),
        )
