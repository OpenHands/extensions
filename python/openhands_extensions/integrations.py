"""Python bindings for the OpenHands extensions integration catalog.

The single source of truth is the unified JSON asset
``integrations/integration-catalog.json``. The JavaScript package
(``@openhands/extensions/integrations``) reads that same asset at runtime, and
this package embeds it (via ``importlib.resources``) and exposes the same API,
so Python and JS consumers read identical data.

Each catalog entry carries one or more ``connectionOptions`` (each an oauth
and/or an mcp/http connector) plus ``supportsOauth`` / ``supportsMcp`` flags.
Use :func:`list_integration_catalog` with the ``mcp`` / ``oauth`` filters to
select entries by connector type (e.g. only integrations that support an oauth
connector).

The asset is generated from the JS authoring source
(``integration-catalog-source.mjs``, which merges the per-integration JSON
files with ``oauth-provider-catalog-source.mjs`` +
``oauth-provider-registration-defaults-source.js``) by
``scripts/build-integration-catalog.mjs``. A parity test
(``tests/test_integration_catalog_in_sync.py``) regenerates the JSON from the
authoring source and asserts the checked-in asset matches, so the two never
drift.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from importlib import resources
from typing import Any, Literal

__all__ = [
    "INTEGRATION_CATALOG_SNAPSHOT",
    "default_managed_connectors",
    "get_oauth_provider_registration_defaults",
    "list_integration_catalog",
    "list_oauth_provider_catalog",
]


@lru_cache(maxsize=1)
def _load_snapshot() -> dict[str, Any]:
    """Load the embedded ``integration-catalog.json`` asset (cached)."""
    with resources.files(__package__).joinpath("integration-catalog.json").open(
        "r", encoding="utf-8"
    ) as handle:
        return json.load(handle)


def _integrations() -> list[dict[str, Any]]:
    return _load_snapshot()["integrations"]


def _providers() -> list[dict[str, Any]]:
    return _load_snapshot()["providers"]


def list_integration_catalog(
    mcp: bool | None = None,
    oauth: bool | None = None,
) -> list[dict[str, Any]]:
    """Return the integration catalog, optionally filtered by connector type.

    Mirrors ``listIntegrationCatalog({ mcp, oauth })`` in
    ``integrations/index.js``. Each entry may expose one or more
    ``connectionOptions``; an entry ``supportsMcp`` if any option is an ``mcp``
    connector and ``supportsOauth`` if any option uses the ``oauth2`` strategy.

    Args:
        mcp: If ``True``, only entries that expose at least one ``mcp``
            connector. If ``False``, only entries that do not. ``None``
            (default) leaves the mcp dimension unfiltered.
        oauth: If ``True``, only entries that expose at least one ``oauth2``
            connector. If ``False``, only entries that do not. ``None``
            (default) leaves the oauth dimension unfiltered.

    Returns:
        A fresh list of matching entries (deep copies), so callers can mutate
        it without corrupting the shared cache.
    """
    if mcp is None and oauth is None:
        return [copy.deepcopy(entry) for entry in _integrations()]
    result = []
    for entry in _integrations():
        if mcp is not None and entry.get("supportsMcp") != mcp:
            continue
        if oauth is not None and entry.get("supportsOauth") != oauth:
            continue
        result.append(copy.deepcopy(entry))
    return result


def list_oauth_provider_catalog() -> list[dict[str, Any]]:
    """Return the OAuth provider catalog (provider-level registration defaults).

    Mirrors ``listOAuthProviderCatalog()`` in ``integrations/index.js``. Reads
    the ``providers`` view from the unified asset. Returns fresh deep copies so
    callers can mutate without corrupting the shared cache.
    """
    return [copy.deepcopy(provider) for provider in _providers()]


def get_oauth_provider_registration_defaults(
    slug: str,
) -> dict[str, Any] | None:
    """Return the registration defaults for ``slug``, or ``None``.

    Mirrors ``getOAuthProviderRegistrationDefaults(slug)`` in
    ``integrations/index.js``. Returns a deep copy so callers can mutate it
    without corrupting the shared cache.
    """
    for provider in _providers():
        if provider["slug"] == slug:
            defaults = provider.get("registrationDefaults")
            return copy.deepcopy(defaults) if defaults is not None else None
    return None


def default_managed_connectors() -> list[dict[str, Any]]:
    """Return the default managed connectors derived from the OAuth provider
    catalog.

    Mirrors the ``defaultManagedConnectors`` array in the unified asset
    (consumed by the integrations-hub backend). Returns a fresh list so callers
    can mutate it without corrupting the shared cache.
    """
    return copy.deepcopy(_load_snapshot()["defaultManagedConnectors"])


#: The raw ``{ integrations, providers, defaultManagedConnectors,
#: defaultManagedConnectorSlugs }`` snapshot, for consumers that want the whole
#: asset in one read (e.g. the integrations-hub backend). Read-only by
#: convention. This is a deep copy of the cached snapshot, so mutating it
#: cannot corrupt the shared cache backing the accessors above.
INTEGRATION_CATALOG_SNAPSHOT: dict[str, Any] = copy.deepcopy(_load_snapshot())


# Kept for type-checker friendliness; the filters only accept booleans/None.
_CatalogFilter = Literal[True, False, None]
