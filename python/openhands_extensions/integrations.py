"""Python bindings for the OpenHands extensions integration catalog.

The single source of truth is the hand-authored JSON asset
``integrations/integration-catalog.json`` (mirrored byte-for-byte into this
package). It is NOT generated from any ``.mjs``/``.js`` source: humans edit it
directly, and each per-integration entry also exists as
``integrations/catalog/<id>.json`` (a CI parity test asserts the two never
drift). The JavaScript package (``@openhands/extensions/integrations``) reads
that same asset at runtime, and this package embeds it (via
``importlib.resources``) and exposes the same API, so Python and JS consumers
read identical data.

The asset stores only canonical, non-duplicated data. Provider-specific OAuth
knowledge that used to live in a separate top-level ``providers[]`` array is
merged into each integration as a minimal ``oauthProvider`` override object
(``null`` when the integration has no OAuth provider). Everything derivable -
``supportsMcp`` / ``supportsOauth``, the reconstructed ``providers[]`` view, and
``defaultManagedConnectors`` - is computed here at runtime so the asset stays
minimal. Use :func:`list_integration_catalog` with the ``mcp`` / ``oauth``
filters to select entries by connector type.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from importlib import resources
from typing import Any

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


def _raw_integrations() -> list[dict[str, Any]]:
    return _load_snapshot()["integrations"]


def _entry_supports_mcp(entry: dict[str, Any]) -> bool:
    return any(option.get("provider") == "mcp" for option in entry.get("connectionOptions", []))


def _entry_supports_oauth(entry: dict[str, Any]) -> bool:
    return any(
        option.get("auth", {}).get("strategy") == "oauth2"
        for option in entry.get("connectionOptions", [])
    )


def _with_derived_flags(entry: dict[str, Any]) -> dict[str, Any]:
    """Attach the derived ``supportsMcp`` / ``supportsOauth`` flags to an entry."""
    enriched = copy.deepcopy(entry)
    enriched["supportsMcp"] = _entry_supports_mcp(entry)
    enriched["supportsOauth"] = _entry_supports_oauth(entry)
    return enriched


def _reconstruct_provider(entry: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct the OAuth-provider view for an integration.

    The provider's identity, UI metadata, and ``registrationDefaults`` already
    live on the integration; ``oauthProvider`` carries only the fields whose
    OAuth-context values differ (``description``, ``docsUrl``,
    ``popularityRank``). ``availability`` is the integration's
    ``catalogStatus``; ``slug`` is the integration ``id``.
    """
    override = entry.get("oauthProvider") or {}
    reconstructed = {
        "slug": entry["id"],
        "name": entry["name"],
        "description": override.get("description", entry.get("description")),
        "categories": entry.get("categories", []),
        "availability": entry.get("catalogStatus"),
        "managedConnectorSlug": entry.get("managedConnectorSlug"),
        "appUrl": entry.get("appUrl"),
        "docsUrl": override.get("docsUrl", entry.get("docsUrl")),
        "notes": entry.get("notes", ""),
        "authStrategy": entry.get("authStrategy", "oauth2"),
        "popularityRank": override.get("popularityRank", entry.get("popularityRank")),
        "registrationDefaults": entry.get("registrationDefaults"),
    }
    return {k: v for k, v in reconstructed.items() if v is not None}


@lru_cache(maxsize=1)
def _providers() -> list[dict[str, Any]]:
    """Reconstruct the OAuth provider catalog from the integrations (cached).

    Each integration with a non-null ``oauthProvider`` yields one provider
    entry whose shape matches the legacy ``providers[]`` contract.
    """
    return [
        _reconstruct_provider(entry)
        for entry in _raw_integrations()
        if entry.get("oauthProvider") is not None
    ]


@lru_cache(maxsize=1)
def _provider_by_slug() -> dict[str, dict[str, Any]]:
    return {p["slug"]: p for p in _providers()}


def _to_default_managed_connector(entry: dict[str, Any]) -> dict[str, Any]:
    provider = _reconstruct_provider(entry)
    defaults = provider.get("registrationDefaults") or {}
    auth_modes = defaults.get("authModes")
    if auth_modes and all(auth_modes):
        resolved_auth_modes = auth_modes
    else:
        resolved_auth_modes = [defaults.get("authStrategy")]
    connector = {
        "slug": provider.get("managedConnectorSlug") or provider["slug"],
        "name": provider["name"],
        "description": provider["description"],
        "appUrl": provider.get("appUrl"),
        "docsUrl": provider.get("docsUrl"),
        "categories": provider.get("categories", []),
        "authModes": resolved_auth_modes,
        "authStrategy": defaults.get("authStrategy"),
        "provider": defaults.get("provider"),
        "credentialLabel": defaults.get("credentialLabel") or f"{provider['name']} credential",
        "credentialPlaceholder": defaults.get("credentialPlaceholder")
        or f"Paste your {provider['name']} credential",
        "credentialHelp": defaults.get("credentialHelp")
        or f"Credential required by {provider['name']}.",
        "apiKeyHeaderName": (defaults.get("apiKeyHeaderName") or "").strip() or None,
        "apiBaseUrl": defaults.get("apiBaseUrl"),
        "openApiUrl": defaults.get("openApiUrl"),
        "serverUrl": defaults.get("serverUrl"),
        "oauthConfigured": True,
    }
    return {k: v for k, v in connector.items() if v is not None}


@lru_cache(maxsize=1)
def _default_managed_connectors() -> list[dict[str, Any]]:
    slugs = _load_snapshot()["defaultManagedConnectorSlugs"]
    by_id = {entry["id"]: entry for entry in _raw_integrations()}
    return [
        _to_default_managed_connector(by_id[slug])
        for slug in slugs
        if slug in by_id
    ]


def list_integration_catalog(
    mcp: bool | None = None,
    oauth: bool | None = None,
) -> list[dict[str, Any]]:
    """Return the integration catalog, optionally filtered by connector type.

    Mirrors ``listIntegrationCatalog({ mcp, oauth })`` in
    ``integrations/index.js``. Each entry may expose one or more
    ``connectionOptions``; an entry ``supportsMcp`` if any option is an ``mcp``
    connector and ``supportsOauth`` if any option uses the ``oauth2`` strategy.
    These flags are derived at runtime from the connection options.

    Args:
        mcp: If ``True``, only entries that expose at least one ``mcp``
            connector. If ``False``, only entries that do not. ``None``
            (default) leaves the mcp dimension unfiltered.
        oauth: If ``True``, only entries that expose at least one ``oauth2``
            connector. If ``False``, only entries that do not. ``None``
            (default) leaves the oauth dimension unfiltered.

    Returns:
        A fresh list of matching entries (deep copies, with derived
        ``supportsMcp`` / ``supportsOauth`` flags attached), so callers can
        mutate it without corrupting the shared cache.
    """
    enriched = [_with_derived_flags(entry) for entry in _raw_integrations()]
    if mcp is None and oauth is None:
        return enriched
    result = []
    for entry in enriched:
        if mcp is not None and entry.get("supportsMcp") != mcp:
            continue
        if oauth is not None and entry.get("supportsOauth") != oauth:
            continue
        result.append(entry)
    return result


def list_oauth_provider_catalog() -> list[dict[str, Any]]:
    """Return the OAuth provider catalog (provider-level registration defaults).

    Mirrors ``listOAuthProviderCatalog()`` in ``integrations/index.js``. The
    provider view is reconstructed at runtime from the integrations: each
    integration with a non-null ``oauthProvider`` yields one provider entry.
    Returns fresh deep copies so callers can mutate without corrupting the
    shared cache.
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
    provider = _provider_by_slug().get(slug)
    if provider is None:
        return None
    defaults = provider.get("registrationDefaults")
    return copy.deepcopy(defaults) if defaults is not None else None


def default_managed_connectors() -> list[dict[str, Any]]:
    """Return the default managed connectors derived from the catalog's
    ``defaultManagedConnectorSlugs``.

    Mirrors ``defaultManagedConnectors()`` in ``integrations/index.js``. Each
    slug is resolved to its integration and materialized from the integration's
    provider view + ``registrationDefaults``. Returns a fresh list so callers
    can mutate it without corrupting the shared cache.
    """
    return copy.deepcopy(_default_managed_connectors())


#: The raw ``{ integrations, defaultManagedConnectorSlugs }`` snapshot, for
#: consumers that want the whole asset in one read (e.g. the integrations-hub
#: backend). Read-only by convention. This is a deep copy of the cached
#: snapshot, so mutating it cannot corrupt the shared cache backing the
#: accessors above. Note this is the *canonical* (non-derived) form: it does
#: NOT include ``supportsMcp`` / ``supportsOauth`` / ``providers`` /
#: ``defaultManagedConnectors``, which are all derived at runtime.
INTEGRATION_CATALOG_SNAPSHOT: dict[str, Any] = copy.deepcopy(_load_snapshot())
