"""Python bindings for the OpenHands extensions catalogs.

Mirrors the JavaScript package (``@openhands/extensions``): both read the same
JSON asset (``integrations/oauth-provider-catalog.json``) so Python and JS
consumers share a single source of truth. See ``integrations.py`` for the
catalog API.
"""

from __future__ import annotations

from ._version import __version__
from .integrations import (
    INTEGRATION_CATALOG_SNAPSHOT,
    default_managed_connectors,
    get_oauth_provider_registration_defaults,
    hubspot_mcp_authorization_url,
    hubspot_mcp_server_url,
    hubspot_mcp_token_url,
    hubspot_optional_scopes,
    hubspot_required_scopes,
    list_oauth_provider_catalog,
)

__all__ = [
    "INTEGRATION_CATALOG_SNAPSHOT",
    "__version__",
    "default_managed_connectors",
    "get_oauth_provider_registration_defaults",
    "hubspot_mcp_authorization_url",
    "hubspot_mcp_server_url",
    "hubspot_mcp_token_url",
    "hubspot_optional_scopes",
    "hubspot_required_scopes",
    "list_oauth_provider_catalog",
]
