"""Versioned deprecation helpers for OpenHands extensions.

This module intentionally mirrors ``openhands.sdk.utils.deprecation`` so public
extension APIs use the same decorator, runtime warning, and model-input
compatibility behavior as the SDK.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from datetime import date
from functools import cache
from importlib.metadata import PackageNotFoundError, version as get_version
from typing import Any, TypeVar, cast

from deprecation import (
    DeprecatedWarning,
    UnsupportedWarning,
    deprecated as _deprecated,
)
from packaging import version as pkg_version


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
    removed_in: str | date | None,
    current_version: str | None = None,
    details: str = "",
) -> Callable[[_FuncT], _FuncT]:
    """Return a decorator that deprecates a callable with explicit metadata."""
    base_decorator = _deprecated(
        deprecated_in=deprecated_in,
        removed_in=removed_in,
        current_version=current_version or _current_version(),
        details=details,
    )

    def decorator(func: _FuncT) -> _FuncT:
        return cast(_FuncT, base_decorator(func))

    return decorator


def _should_warn(
    *,
    deprecated_in: str | None,
    removed_in: str | date | None,
    current_version: str | None,
) -> tuple[bool, bool]:
    is_deprecated = False
    is_unsupported = False

    if isinstance(removed_in, date):
        if date.today() >= removed_in:
            is_unsupported = True
        else:
            is_deprecated = True
    elif current_version:
        current = pkg_version.parse(current_version)
        if removed_in and current >= pkg_version.parse(str(removed_in)):
            is_unsupported = True
        elif deprecated_in and current >= pkg_version.parse(deprecated_in):
            is_deprecated = True
    else:
        is_deprecated = True

    return is_deprecated, is_unsupported


def warn_deprecated(
    feature: str,
    *,
    deprecated_in: str,
    removed_in: str | date | None,
    current_version: str | None = None,
    details: str = "",
    stacklevel: int = 2,
) -> None:
    """Emit a deprecation warning for dynamic access to a legacy feature."""
    current_version = current_version or _current_version()
    is_deprecated, is_unsupported = _should_warn(
        deprecated_in=deprecated_in,
        removed_in=removed_in,
        current_version=current_version,
    )

    if not (is_deprecated or is_unsupported):
        return

    warning_cls = UnsupportedWarning if is_unsupported else DeprecatedWarning
    warning = warning_cls(feature, deprecated_in, removed_in, details)
    warnings.warn(warning, stacklevel=stacklevel)


def warn_cleanup(
    workaround: str,
    *,
    cleanup_by: str | date,
    current_version: str | None = None,
    details: str = "",
    stacklevel: int = 2,
) -> None:
    """Emit a warning when a temporary workaround has reached its deadline."""
    current_version = current_version or _current_version()

    should_cleanup = False
    if isinstance(cleanup_by, date):
        should_cleanup = date.today() >= cleanup_by
    else:
        try:
            current = pkg_version.parse(current_version)
            target = pkg_version.parse(str(cleanup_by))
            should_cleanup = current >= target
        except pkg_version.InvalidVersion:
            pass

    if should_cleanup:
        message = (
            f"Cleanup required: {workaround}. "
            f"This workaround was scheduled for removal by {cleanup_by}."
        )
        if details:
            message += f" {details}"
        warnings.warn(message, UserWarning, stacklevel=stacklevel)


def handle_deprecated_model_fields(
    data: Any,
    deprecated_fields: tuple[str, ...],
) -> Any:
    """Remove permanently supported legacy fields from Pydantic model input."""
    if not isinstance(data, dict):
        return data

    for field in deprecated_fields:
        data.pop(field, None)

    return data


__all__ = [
    "deprecated",
    "warn_deprecated",
    "warn_cleanup",
    "handle_deprecated_model_fields",
]
