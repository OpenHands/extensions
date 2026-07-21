"""Package version, derived from installed package metadata.

The single source of truth is ``pyproject.toml``'s ``[project].version``
(which ``release-please`` bumps together with ``package.json`` via
``release-please-config.json`` -> ``extra-files``). At runtime we read the
installed distribution metadata via ``importlib.metadata`` so there is no
second hand-maintained version string. ``_FALLBACK_VERSION`` is only used
when the package is imported without being installed (e.g. straight off a
source checkout with no build), and ``tests/test_version_alignment.py``
asserts it stays in lock-step with ``pyproject.toml`` / ``package.json``.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

#: Fallback used only when the package is not installed (no dist metadata).
#: Kept in lock-step with pyproject.toml/package.json by the version test.
# x-release-please-version
_FALLBACK_VERSION = "0.11.0"

try:
    __version__: str = version("openhands-extensions")
except PackageNotFoundError:  # not installed (e.g. raw source checkout)
    __version__ = _FALLBACK_VERSION
