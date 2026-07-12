"""Versioned deprecation helpers for the public Python bindings.

This intentionally follows the OpenHands SDK convention: every deprecation
declares both the first deprecated version and the scheduled removal version.
The companion ``scripts/check_deprecations.py`` guard fails a release PR once
the scheduled version is reached.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import cache
from importlib.metadata import PackageNotFoundError, version as get_version
from typing import Any, TypeVar, cast

from deprecation import deprecated as _deprecated


_FuncT = TypeVar("_FuncT", bound=Callable[..., Any])


@cache
def _current_version() -> str:
    try:
        return get_version("openhands-extensions")
    except PackageNotFoundError:
        return "0.0.0"


def deprecated(
    *,
    deprecated_in: str,
    removed_in: str | None,
    current_version: str | None = None,
    details: str = "",
) -> Callable[[_FuncT], _FuncT]:
    """Decorate a public callable with explicit versioned deprecation metadata."""

    base_decorator = _deprecated(
        deprecated_in=deprecated_in,
        removed_in=removed_in,
        current_version=current_version or _current_version(),
        details=details,
    )

    def decorator(func: _FuncT) -> _FuncT:
        return cast(_FuncT, base_decorator(func))

    return decorator


__all__ = ["deprecated"]
