"""Python bindings for the OpenHands extensions catalogs.

Mirrors the JavaScript package (``@openhands/extensions``): both read the same
unified JSON asset (``integrations/integration-catalog.json``) at runtime, so
Python and JS consumers share a single source of truth. The asset is generated
from the JS authoring source by ``scripts/build-integration-catalog.mjs``; a CI
parity test asserts the checked-in copy matches a fresh build. See
``integrations.py`` for the catalog API, including filtering by connector type
(mcp / oauth).
"""

from __future__ import annotations

from ._version import __version__
from .integrations import (
    INTEGRATION_CATALOG_SNAPSHOT,
    default_managed_connectors,
    get_oauth_provider_registration_defaults,
    list_integration_catalog,
    list_oauth_provider_catalog,
)

__all__ = [
    "INTEGRATION_CATALOG_SNAPSHOT",
    "__version__",
    "default_managed_connectors",
    "get_oauth_provider_registration_defaults",
    "list_integration_catalog",
    "list_oauth_provider_catalog",
]
