"""Python bindings for the OpenHands extensions catalogs.

Mirrors the JavaScript package (``@openhands/extensions``): both read the same
JSON asset (``integrations/oauth-provider-catalog.json``) so Python and JS
consumers share a single source of truth. See ``integrations.py`` for the
catalog API.
"""

from __future__ import annotations

from ._version import __version__
from .integrations import (
    HUBSPOT_MCP_AUTHORIZATION_URL,
    HUBSPOT_MCP_SERVER_URL,
    HUBSPOT_MCP_TOKEN_URL,
    HUBSPOT_OPTIONAL_SCOPES,
    HUBSPOT_REQUIRED_SCOPES,
    INTEGRATION_CATALOG_SNAPSHOT,
    default_managed_connectors,
    get_oauth_provider_registration_defaults,
    list_oauth_provider_catalog,
)

__all__ = [
    "HUBSPOT_MCP_AUTHORIZATION_URL",
    "HUBSPOT_MCP_SERVER_URL",
    "HUBSPOT_MCP_TOKEN_URL",
    "HUBSPOT_OPTIONAL_SCOPES",
    "HUBSPOT_REQUIRED_SCOPES",
    "INTEGRATION_CATALOG_SNAPSHOT",
    "__version__",
    "default_managed_connectors",
    "get_oauth_provider_registration_defaults",
    "list_oauth_provider_catalog",
]
