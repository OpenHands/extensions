"""Assert the checked-in ``oauth-provider-catalog.json`` asset stays in sync
with the JavaScript authoring source, and that the Python package reads the
same data.

The JSON asset is the single source of truth shared by the JS and Python
packages. It is generated from the JS source by
``scripts/build-integration-catalog.mjs``. This test regenerates it and
asserts the checked-in copy matches, so a catalog edit that forgets to
re-run the build fails CI.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import openhands_extensions

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "integrations" / "oauth-provider-catalog.json"
BUILD_SCRIPT = ROOT / "scripts" / "build-integration-catalog.mjs"


def _run_node_dump() -> dict:
    """Regenerate the catalog via the JS build script and return it parsed."""
    result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            (
                "import { buildCatalog } from "
                f"{BUILD_SCRIPT.as_posix()!r};\n"
                "process.stdout.write(JSON.stringify(buildCatalog()));"
            ),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_checked_in_asset_matches_js_source() -> None:
    """The committed JSON must equal a fresh build from the JS source."""
    regenerated = _run_node_dump()
    checked_in = json.loads(ASSET.read_text())
    assert checked_in == regenerated, (
        "integrations/oauth-provider-catalog.json is out of sync with the JS "
        "source. Run `npm run build:integration-catalog` and commit the result."
    )


def test_python_reads_the_same_asset() -> None:
    """The Python package must load the checked-in JSON asset verbatim."""
    checked_in = json.loads(ASSET.read_text())
    assert openhands_extensions.INTEGRATION_CATALOG_SNAPSHOT == checked_in


def test_python_list_oauth_provider_catalog_matches_asset() -> None:
    checked_in = json.loads(ASSET.read_text())
    assert openhands_extensions.list_oauth_provider_catalog() == checked_in["providers"]


def test_python_default_managed_connectors_match_asset() -> None:
    checked_in = json.loads(ASSET.read_text())
    assert (
        openhands_extensions.default_managed_connectors()
        == checked_in["defaultManagedConnectors"]
    )


def test_get_oauth_provider_registration_defaults_round_trip() -> None:
    for provider in openhands_extensions.list_oauth_provider_catalog():
        slug = provider["slug"]
        defaults = openhands_extensions.get_oauth_provider_registration_defaults(slug)
        assert defaults == provider["registrationDefaults"]


def test_get_oauth_provider_registration_defaults_unknown_slug() -> None:
    assert openhands_extensions.get_oauth_provider_registration_defaults("nope") is None


def test_hubspot_constants_match_asset() -> None:
    """The HubSpot module-level constants must match the hubspot entry's
    registrationDefaults in the asset (they are convenience aliases, not a
    second source of truth)."""
    hubspot = openhands_extensions.get_oauth_provider_registration_defaults("hubspot")
    assert hubspot is not None
    assert openhands_extensions.HUBSPOT_MCP_SERVER_URL == hubspot["serverUrl"]
    assert openhands_extensions.HUBSPOT_MCP_AUTHORIZATION_URL == hubspot["authorizationUrl"]
    assert openhands_extensions.HUBSPOT_MCP_TOKEN_URL == hubspot["tokenUrl"]
    assert openhands_extensions.HUBSPOT_REQUIRED_SCOPES == list(hubspot.get("scopes", []))
    assert openhands_extensions.HUBSPOT_OPTIONAL_SCOPES == list(
        hubspot.get("optionalScopes", [])
    )


def test_hubspot_constants_are_values_not_callables() -> None:
    """Guard against regressing the public API back to callables (review
    feedback: names like ``hubspot_mcp_server_url`` must be the string, not a
    function returning it)."""
    import openhands_extensions as ext

    assert isinstance(ext.HUBSPOT_MCP_SERVER_URL, str)
    assert isinstance(ext.HUBSPOT_MCP_TOKEN_URL, str)
    assert isinstance(ext.HUBSPOT_REQUIRED_SCOPES, list)
    assert all(isinstance(s, str) for s in ext.HUBSPOT_REQUIRED_SCOPES)
