"""Python bindings for the OpenHands extensions integration catalog.

The source of truth is the hand-authored ``integrations/catalog/<id>.json``
directory. Wheels include those individual JSON files directly; no aggregate
catalog JSON is authored or packaged.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, Iterable

__all__ = [
    "INTEGRATION_CATALOG_SNAPSHOT",
    "get_integration_catalog_entry",
    "list_integration_catalog",
]


def _repo_catalog_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "integrations" / "catalog"


def _catalog_files() -> Iterable[Any]:
    packaged = resources.files(__package__).joinpath("catalog")
    if packaged.is_dir():
        return sorted(
            (path for path in packaged.iterdir() if path.name.endswith(".json")),
            key=lambda path: path.name,
        )

    repo_catalog = _repo_catalog_dir()
    return sorted(repo_catalog.glob("*.json"), key=lambda path: path.name)


def _read_json(path: Any) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _integrations() -> tuple[dict[str, Any], ...]:
    entries = [_read_json(path) for path in _catalog_files()]
    entries.sort(
        key=lambda entry: (-(entry.get("popularityRank") if entry.get("popularityRank") is not None else -1), entry["id"]),
    )
    return tuple(entries)


@lru_cache(maxsize=1)
def _integration_by_id() -> dict[str, dict[str, Any]]:
    return {entry["id"]: entry for entry in _integrations()}


def _entry_supports_mcp(entry: dict[str, Any]) -> bool:
    return any(option.get("provider") == "mcp" for option in entry.get("connectionOptions", []))


def _entry_supports_oauth(entry: dict[str, Any]) -> bool:
    return any(
        option.get("auth", {}).get("strategy") == "oauth2"
        for option in entry.get("connectionOptions", [])
    )


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


INTEGRATION_CATALOG_SNAPSHOT: dict[str, Any] = {
    "integrations": copy.deepcopy(list(_integrations()))
}
