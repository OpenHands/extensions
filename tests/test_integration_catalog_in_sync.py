"""Assert the checked-in ``integration-catalog.json`` asset is the single
source of truth shared by the JS and Python packages.

The unified JSON asset is generated from the JS authoring source by
``scripts/build-integration-catalog.mjs``. This test regenerates it and
asserts the checked-in copy matches, so a catalog edit that forgets to
re-run the build fails CI. It also asserts the JS runtime accessors return
the same data as the Python accessors (both read the JSON), and that the
filter accessors (mcp / oauth) select the right entries.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import openhands_extensions

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "integrations" / "integration-catalog.json"
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
    """The committed JSON must equal a fresh build from the JS authoring source."""
    regenerated = _run_node_dump()
    checked_in = json.loads(ASSET.read_text())
    assert checked_in == regenerated, (
        "integrations/integration-catalog.json is out of sync with the JS "
        "authoring source. Run `npm run build:integration-catalog` and commit "
        "the result."
    )


def test_python_reads_the_same_asset() -> None:
    """The Python package must load the checked-in JSON asset verbatim."""
    checked_in = json.loads(ASSET.read_text())
    assert openhands_extensions.INTEGRATION_CATALOG_SNAPSHOT == checked_in


def test_python_list_integration_catalog_matches_asset() -> None:
    checked_in = json.loads(ASSET.read_text())
    assert openhands_extensions.list_integration_catalog() == checked_in["integrations"]


def test_python_list_oauth_provider_catalog_matches_asset() -> None:
    checked_in = json.loads(ASSET.read_text())
    assert openhands_extensions.list_oauth_provider_catalog() == checked_in["providers"]


def test_python_default_managed_connectors_match_asset() -> None:
    checked_in = json.loads(ASSET.read_text())
    assert (
        openhands_extensions.default_managed_connectors()
        == checked_in["defaultManagedConnectors"]
    )
    assert checked_in["defaultManagedConnectorSlugs"] == [
        c["slug"] for c in checked_in["defaultManagedConnectors"]
    ]


def test_get_oauth_provider_registration_defaults_round_trip() -> None:
    for provider in openhands_extensions.list_oauth_provider_catalog():
        slug = provider["slug"]
        defaults = openhands_extensions.get_oauth_provider_registration_defaults(slug)
        assert defaults == provider.get("registrationDefaults")


def test_get_oauth_provider_registration_defaults_unknown_slug() -> None:
    assert openhands_extensions.get_oauth_provider_registration_defaults("nope") is None


def test_python_asset_is_byte_identical_to_root_asset() -> None:
    """The Python package's bundled asset must be byte-identical to the root
    generated asset. The build script writes both from a single generation
    pass; this guards against a maintainer updating one copy without the other
    (which would ship a stale catalog in the wheel)."""
    root_asset = (ROOT / "integrations" / "integration-catalog.json").read_bytes()
    py_asset = (
        ROOT / "python" / "openhands_extensions" / "integration-catalog.json"
    ).read_bytes()
    assert root_asset == py_asset, (
        "Python package asset drifts from the root asset. Re-run "
        "`npm run build:integration-catalog` (it writes both copies)."
    )


def _js_call(expr: str) -> str:
    """Run a JS expression against the runtime package and return stdout."""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", expr],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    return result.stdout


def test_js_reads_the_same_asset_as_python() -> None:
    """The JS runtime accessors must return the same data as the Python
    accessors: both read the unified JSON asset (single source of truth)."""
    asset = json.loads(ASSET.read_text())
    integrations = _js_call(
        "import { listIntegrationCatalog } from './integrations/index.js';\n"
        "process.stdout.write(JSON.stringify(listIntegrationCatalog()));"
    )
    assert json.loads(integrations) == asset["integrations"]
    assert openhands_extensions.list_integration_catalog() == asset["integrations"]

    providers = _js_call(
        "import { listOAuthProviderCatalog } from './integrations/index.js';\n"
        "process.stdout.write(JSON.stringify(listOAuthProviderCatalog()));"
    )
    assert json.loads(providers) == asset["providers"]
    assert openhands_extensions.list_oauth_provider_catalog() == asset["providers"]

    connectors = _js_call(
        "import { defaultManagedConnectors } from './integrations/index.js';\n"
        "process.stdout.write(JSON.stringify(defaultManagedConnectors()));"
    )
    assert json.loads(connectors) == asset["defaultManagedConnectors"]
    assert openhands_extensions.default_managed_connectors() == asset["defaultManagedConnectors"]


def _js_filter(mcp, oauth) -> list[str]:
    expr = (
        "import { listIntegrationCatalog } from './integrations/index.js';\n"
        f"const f = listIntegrationCatalog({{ mcp: {mcp}, oauth: {oauth} }});\n"
        "process.stdout.write(JSON.stringify(f.map((e) => e.id)));"
    )
    return json.loads(_js_call(expr))


def test_filter_mcp_only() -> None:
    """`mcp: true` selects exactly the entries flagged supportsMcp, in JS and Python."""
    py_ids = {e["id"] for e in openhands_extensions.list_integration_catalog(mcp=True)}
    js_ids = set(_js_filter("true", "undefined"))
    all_mcp = {
        e["id"] for e in openhands_extensions.list_integration_catalog() if e["supportsMcp"]
    }
    assert py_ids == js_ids == all_mcp
    assert "filesystem" in py_ids  # stdio mcp, no oauth


def test_filter_oauth_only() -> None:
    """`oauth: true` selects exactly the entries flagged supportsOauth."""
    py_ids = {e["id"] for e in openhands_extensions.list_integration_catalog(oauth=True)}
    js_ids = set(_js_filter("undefined", "true"))
    all_oauth = {
        e["id"]
        for e in openhands_extensions.list_integration_catalog()
        if e["supportsOauth"]
    }
    assert py_ids == js_ids == all_oauth
    assert "github" in py_ids


def test_filter_oauth_not_mcp() -> None:
    """`oauth: true, mcp: false` selects oauth-only (non-mcp) entries."""
    py_ids = {e["id"] for e in openhands_extensions.list_integration_catalog(oauth=True, mcp=False)}
    js_ids = set(_js_filter("false", "true"))
    expected = {
        e["id"]
        for e in openhands_extensions.list_integration_catalog()
        if e["supportsOauth"] and not e["supportsMcp"]
    }
    assert py_ids == js_ids == expected


def test_filter_none_returns_all() -> None:
    """No filter (or all-None) returns the full catalog."""
    assert len(openhands_extensions.list_integration_catalog()) == len(
        openhands_extensions.list_integration_catalog(mcp=None, oauth=None)
    )
    js_all = json.loads(_js_call(
        "import { listIntegrationCatalog } from './integrations/index.js';\n"
        "process.stdout.write(JSON.stringify(listIntegrationCatalog().length));"
    ))
    assert js_all == len(openhands_extensions.list_integration_catalog())


def test_accessors_return_independent_copies() -> None:
    """The cached accessors must return independent objects so a caller mutating
    a returned value cannot corrupt the shared cache for other callers."""
    catalog_a = openhands_extensions.list_integration_catalog()
    catalog_b = openhands_extensions.list_integration_catalog()
    assert catalog_a == catalog_b
    assert catalog_a is not catalog_b
    catalog_a[0]["__mutated"] = True
    assert "__mutated" not in openhands_extensions.list_integration_catalog()[0]

    defaults_a = openhands_extensions.get_oauth_provider_registration_defaults("github")
    assert defaults_a is not None
    defaults_a["__mutated"] = True
    defaults_b = openhands_extensions.get_oauth_provider_registration_defaults("github")
    assert defaults_b is not None
    assert "__mutated" not in defaults_b

    connectors_a = openhands_extensions.default_managed_connectors()
    connectors_b = openhands_extensions.default_managed_connectors()
    assert connectors_a is not connectors_b

    # INTEGRATION_CATALOG_SNAPSHOT is a deep copy of the cached snapshot, so
    # mutating it must not affect the accessors (which read the cache).
    snapshot = openhands_extensions.INTEGRATION_CATALOG_SNAPSHOT
    snapshot["integrations"][0]["__mutated"] = True
    assert (
        "__mutated"
        not in openhands_extensions.list_integration_catalog()[0]
    )
