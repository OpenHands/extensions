"""Assert the JS (``package.json``) and Python (``pyproject.toml`` +
``_version.py``) package versions never drift apart.

``release-please`` is configured to bump both ``package.json`` and
``pyproject.toml`` together (see ``release-please-config.json`` ->
``extra-files``). This test is the guard that catches a manual edit that
bumps only one.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _package_json_version() -> str:
    text = (ROOT / "package.json").read_text()
    match = re.search(r'"version"\s*:\s*"([^"]+)"', text)
    assert match, "package.json has no version field"
    return match.group(1)


def _pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "pyproject.toml has no version field"
    return match.group(1)


def _version_module_version() -> str:
    text = (ROOT / "python" / "openhands_extensions" / "_version.py").read_text()
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    assert match, "_version.py has no __version__"
    return match.group(1)


def test_package_json_and_pyproject_versions_match() -> None:
    assert _package_json_version() == _pyproject_version(), (
        "package.json and pyproject.toml versions differ. release-please "
        "should bump both together; check release-please-config.json."
    )


def test_version_module_matches_package_json() -> None:
    assert _version_module_version() == _package_json_version(), (
        "python/openhands_extensions/_version.py is out of sync with "
        "package.json."
    )


def test_installed_package_version_matches_source() -> None:
    import openhands_extensions

    assert openhands_extensions.__version__ == _package_json_version()
