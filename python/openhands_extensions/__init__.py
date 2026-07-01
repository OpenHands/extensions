"""Python bindings for the OpenHands extensions catalogs.

Mirrors the JavaScript package (``@openhands/extensions``): both read the same
hand-authored ``integrations/catalog/<id>.json`` files. The JavaScript package
uses a generated static import index; the Python package loads the packaged
individual JSON files directly. See ``integrations.py`` for the catalog API,
including filtering by connector type (mcp / oauth).
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
