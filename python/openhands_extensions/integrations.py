"""Python bindings for the OpenHands extensions integration catalog.

The source of truth is the hand-authored ``integrations/catalog/<id>.json``
directory. ``integration-catalog.json`` is a generated package asset assembled
from that directory and mirrored byte-for-byte into this package.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from importlib import resources
from typing import Any

__all__ = [
    "INTEGRATION_CATALOG_SNAPSHOT",
    "get_integration_catalog_entry",
    "list_integration_catalog",
]


@lru_cache(maxsize=1)
def _load_snapshot() -> dict[str, Any]:
    with resources.files(__package__).joinpath("integration-catalog.json").open(
        "r", encoding="utf-8"
    ) as handle:
        return json.load(handle)


def _raw_integrations() -> list[dict[str, Any]]:
    return _load_snapshot()["integrations"]


def _entry_supports_mcp(entry: dict[str, Any]) -> bool:
    return any(option.get("provider") == "mcp" for option in entry.get("connectionOptions", []))


def _entry_supports_oauth(entry: dict[str, Any]) -> bool:
    return any(
        option.get("auth", {}).get("strategy") == "oauth2"
        for option in entry.get("connectionOptions", [])
    )


@lru_cache(maxsize=1)
def _integrations() -> tuple[dict[str, Any], ...]:
    return tuple(_raw_integrations())


@lru_cache(maxsize=1)
def _integration_by_id() -> dict[str, dict[str, Any]]:
    return {entry["id"]: entry for entry in _integrations()}


def list_integration_catalog(
    mcp: bool | None = None,
    oauth: bool | None = None,
) -> list[dict[str, Any]]:
    """Return the integration catalog, optionally filtered by connector type."""
    result = []
    for entry in _integrations():
        if mcp is not None and _entry_supports_mcp(entry) != mcp:
            continue
        if oauth is not None and _entry_supports_oauth(entry) != oauth:
            continue
        result.append(copy.deepcopy(entry))
    return result


def get_integration_catalog_entry(id: str) -> dict[str, Any] | None:
    """Return one integration catalog entry by id, or ``None``."""
    entry = _integration_by_id().get(id)
    return copy.deepcopy(entry) if entry is not None else None


INTEGRATION_CATALOG_SNAPSHOT: dict[str, Any] = copy.deepcopy(_load_snapshot())
