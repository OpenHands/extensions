"""Python bindings for the OpenHands extensions catalogs.

Mirrors the JavaScript package (``@openhands/extensions``): both read the same
hand-authored JSON asset (``integrations/integration-catalog.json``) at runtime,
so Python and JS consumers share a single source of truth. The asset is NOT
generated from any ``.mjs``/``.js`` source; each per-integration entry also
exists as ``integrations/catalog/<id>.json`` (a CI parity test asserts the two
never drift). See
``integrations.py`` for the catalog API, including filtering by connector type
(mcp / oauth).
"""

from __future__ import annotations

from ._version import __version__
from .integrations import (
    INTEGRATION_CATALOG_SNAPSHOT,
    get_integration_catalog_entry,
    list_integration_catalog,
)

__all__ = [
    "INTEGRATION_CATALOG_SNAPSHOT",
    "__version__",
    "get_integration_catalog_entry",
    "list_integration_catalog",
]
