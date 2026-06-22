"""Python bindings for the OpenHands extensions catalogs.

Mirrors the JavaScript package (``@openhands/extensions``): both read the same
generated ``integration-catalog.json`` package asset at runtime. The manually
edited source of truth is the ``integrations/catalog/<id>.json`` directory;
``scripts/build-integration-catalog.mjs`` assembles the generated JS/Python
assets from those files. See ``integrations.py`` for the catalog API, including
filtering by connector type (mcp / oauth).
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
