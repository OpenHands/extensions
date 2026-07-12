"""Tests for the public deprecation policy and its release-please guard."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from deprecation import DeprecatedWarning

from openhands_extensions.deprecation import deprecated


ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "check_deprecations.py"


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


def test_release_please_deadline_passes_before_removal_version() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECK), "--current-version", "0.10.0"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_release_please_deadline_fails_at_removal_version() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECK), "--current-version", "0.12.0"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "list_integration_catalog" in result.stdout
    assert "get_integration_catalog_entry" in result.stdout
