"""Python bindings for the OpenHands extensions integration catalog.

The single source of truth is the JSON asset
``integrations/oauth-provider-catalog.json``, generated from the JavaScript
authoring source by ``scripts/build-integration-catalog.mjs``. This package
embeds that asset (via ``importlib.resources``) and exposes the same API the
JS package (``@openhands/extensions/integrations``) exposes, so Python and JS
consumers read identical data.

A parity test (``tests/test_integration_catalog_in_sync.py``) regenerates the
JSON from the JS source and asserts the checked-in asset matches, so the two
never drift.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any

__all__ = [
    "INTEGRATION_CATALOG_SNAPSHOT",
    "default_managed_connectors",
    "get_oauth_provider_registration_defaults",
    "hubspot_mcp_authorization_url",
    "hubspot_mcp_server_url",
    "hubspot_mcp_token_url",
    "hubspot_optional_scopes",
    "hubspot_required_scopes",
    "list_oauth_provider_catalog",
]


@lru_cache(maxsize=1)
def _load_snapshot() -> dict[str, Any]:
    """Load the embedded ``oauth-provider-catalog.json`` asset."""
    with resources.files(__package__).joinpath("oauth-provider-catalog.json").open(
        "r", encoding="utf-8"
    ) as handle:
        return json.load(handle)


def _providers() -> list[dict[str, Any]]:
    return _load_snapshot()["providers"]


def list_oauth_provider_catalog() -> list[dict[str, Any]]:
    """Return the full OAuth provider catalog.

    Mirrors ``listOAuthProviderCatalog()`` in
    ``integrations/oauth-provider-catalog.js``.
    """
    return _providers()


def get_oauth_provider_registration_defaults(
    slug: str,
) -> dict[str, Any] | None:
    """Return the registration defaults for ``slug``, or ``None``.

    Mirrors ``getOAuthProviderRegistrationDefaults(slug)`` in
    ``integrations/oauth-provider-registration-defaults.js``.
    """
    for provider in _providers():
        if provider["slug"] == slug:
            return provider.get("registrationDefaults")
    return None


def default_managed_connectors() -> list[dict[str, Any]]:
    """Return the default managed connectors derived from the catalog.

    Mirrors the ``defaultManagedConnectors`` array produced by
    ``scripts/build-integration-catalog.mjs`` (and consumed by the
    integrations-hub backend).
    """
    return _load_snapshot()["defaultManagedConnectors"]


def _hubspot_defaults() -> dict[str, Any]:
    defaults = get_oauth_provider_registration_defaults("hubspot")
    if defaults is None:
        raise RuntimeError("hubspot provider missing from oauth-provider-catalog.json")
    return defaults


#: HubSpot MCP endpoint constants (mirror the JS ``hubspotMcp*`` exports).
#: Exposed as plain values, not callables, to match the JS constant semantics.
HUBSPOT_MCP_SERVER_URL: str = _hubspot_defaults()["serverUrl"]
HUBSPOT_MCP_AUTHORIZATION_URL: str = _hubspot_defaults()["authorizationUrl"]
HUBSPOT_MCP_TOKEN_URL: str = _hubspot_defaults()["tokenUrl"]
HUBSPOT_REQUIRED_SCOPES: list[str] = list(_hubspot_defaults().get("scopes", []))
HUBSPOT_OPTIONAL_SCOPES: list[str] = list(_hubspot_defaults().get("optionalScopes", []))


#: The raw ``{ providers, defaultManagedConnectors }`` snapshot, for consumers
#: that want the whole asset in one read (e.g. the integrations-hub backend).
INTEGRATION_CATALOG_SNAPSHOT: dict[str, Any] = _load_snapshot()
