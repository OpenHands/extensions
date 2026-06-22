"""Assert the checked-in ``integration-catalog.json`` asset is the single
source of truth shared by the JS and Python packages.

The unified JSON asset is hand-authored (NOT generated from any ``.mjs``/``.js``
source). This test asserts:

* the asset is internally consistent (each ``integrations/catalog/<id>.json``
  file equals the matching integration entry in the master asset, and the
  Python-bundled copy is byte-identical to the root asset);
* the JS runtime accessors return the same data as the Python accessors (both
  read the JSON); the derived ``supportsMcp``/``supportsOauth`` flags,
  reconstructed ``providers[]`` view, and ``defaultManagedConnectors`` agree;
* the filter accessors (mcp / oauth) select the right entries.

Provider-specific OAuth knowledge lives on each integration as a minimal
``oauthProvider`` override; the provider view is reconstructed at runtime by
``listOAuthProviderCatalog()``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import openhands_extensions

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "integrations" / "integration-catalog.json"
CATALOG_DIR = ROOT / "integrations" / "catalog"


def test_asset_is_hand_authored_source_of_truth() -> None:
    """The asset has the canonical (non-derived) shape: integrations with merged
    ``oauthProvider`` and a ``defaultManagedConnectorSlugs`` list. No
    ``providers``/``defaultManagedConnectors``/per-entry ``supportsMcp``
    arrays/fields are stored - they are derived at runtime."""
    checked_in = json.loads(ASSET.read_text())
    assert set(checked_in.keys()) == {"integrations", "defaultManagedConnectorSlugs"}
    for entry in checked_in["integrations"]:
        assert "supportsMcp" not in entry
        assert "supportsOauth" not in entry
        # oauthProvider is null iff the integration has no OAuth provider.
        assert "oauthProvider" in entry


def test_catalog_files_match_master_entries() -> None:
    """Every ``integrations/catalog/<id>.json`` must equal the matching
    integration entry in the master asset, and every integration must have a
    catalog file. This keeps the per-integration public files in sync with the
    hand-authored master (no mjs generation involved)."""
    master = {e["id"]: e for e in json.loads(ASSET.read_text())["integrations"]}
    catalog_files = {p.stem: json.loads(p.read_text()) for p in CATALOG_DIR.glob("*.json")}
    assert set(catalog_files) == set(master), (
        f"catalog/*.json ids != master integration ids: "
        f"only-in-catalog={set(catalog_files) - set(master)}, "
        f"only-in-master={set(master) - set(catalog_files)}"
    )
    for integration_id, entry in master.items():
        assert catalog_files[integration_id] == entry, (
            f"integrations/catalog/{integration_id}.json drifts from master entry"
        )


def test_python_reads_the_same_asset() -> None:
    """The Python package must load the checked-in JSON asset verbatim."""
    checked_in = json.loads(ASSET.read_text())
    assert openhands_extensions.INTEGRATION_CATALOG_SNAPSHOT == checked_in


def test_python_list_integration_catalog_derives_flags() -> None:
    """list_integration_catalog attaches the derived supportsMcp/supportsOauth
    flags (absent from the stored asset) and returns all entries."""
    entries = openhands_extensions.list_integration_catalog()
    assert len(entries) == len(json.loads(ASSET.read_text())["integrations"])
    for entry in entries:
        assert isinstance(entry["supportsMcp"], bool)
        assert isinstance(entry["supportsOauth"], bool)


def test_python_default_managed_connectors_match_slugs() -> None:
    checked_in = json.loads(ASSET.read_text())
    connectors = openhands_extensions.default_managed_connectors()
    assert [c["slug"] for c in connectors] == checked_in["defaultManagedConnectorSlugs"]


def test_get_oauth_provider_registration_defaults_round_trip() -> None:
    for provider in openhands_extensions.list_oauth_provider_catalog():
        slug = provider["slug"]
        defaults = openhands_extensions.get_oauth_provider_registration_defaults(slug)
        assert defaults == provider.get("registrationDefaults")


def test_get_oauth_provider_registration_defaults_unknown_slug() -> None:
    assert openhands_extensions.get_oauth_provider_registration_defaults("nope") is None


def test_python_asset_is_byte_identical_to_root_asset() -> None:
    """The Python package's bundled asset must be byte-identical to the root
    asset so a stale catalog is never shipped in the wheel."""
    root_asset = (ROOT / "integrations" / "integration-catalog.json").read_bytes()
    py_asset = (
        ROOT / "python" / "openhands_extensions" / "integration-catalog.json"
    ).read_bytes()
    assert root_asset == py_asset, (
        "Python package asset drifts from the root asset. Copy the root "
        "asset to python/openhands_extensions/integration-catalog.json."
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
    accessors: both read the unified JSON asset (single source of truth) and
    derive the same views (including the supportsMcp/supportsOauth flags)."""
    integrations = _js_call(
        "import { listIntegrationCatalog } from './integrations/index.js';\n"
        "process.stdout.write(JSON.stringify(listIntegrationCatalog()));"
    )
    assert json.loads(integrations) == openhands_extensions.list_integration_catalog()

    providers = _js_call(
        "import { listOAuthProviderCatalog } from './integrations/index.js';\n"
        "process.stdout.write(JSON.stringify(listOAuthProviderCatalog()));"
    )
    assert json.loads(providers) == openhands_extensions.list_oauth_provider_catalog()

    connectors = _js_call(
        "import { defaultManagedConnectors } from './integrations/index.js';\n"
        "process.stdout.write(JSON.stringify(defaultManagedConnectors()));"
    )
    assert json.loads(connectors) == openhands_extensions.default_managed_connectors()


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


def test_oauth_provider_override_minimal_and_null() -> None:
    """oauthProvider is null for non-oauth integrations and carries only
    differing fields (description/docsUrl/popularityRank) for oauth ones."""
    entries = {e["id"]: e for e in openhands_extensions.list_integration_catalog()}
    # filesystem has no oauth provider.
    assert entries["filesystem"]["oauthProvider"] is None
    # github has an oauth provider with differing description/docsUrl/popularityRank.
    github_ov = entries["github"]["oauthProvider"]
    assert github_ov is not None
    assert set(github_ov.keys()) <= {"description", "docsUrl", "popularityRank"}
    # every reconstructed provider round-trips to a non-null oauthProvider entry.
    provider_ids = {p["slug"] for p in openhands_extensions.list_oauth_provider_catalog()}
    oauth_entry_ids = {i for i, e in entries.items() if e["oauthProvider"] is not None}
    assert provider_ids == oauth_entry_ids


def test_hubspot_managed_connector_migration_removed() -> None:
    """Regression guard for the original critical review finding: the legacy
    ``managedConnectorMigration`` mechanism is gone; HubSpot's OAuth config is
    declared as data on the integration, and the registration defaults are
    retrievable via the accessor."""
    defaults = openhands_extensions.get_oauth_provider_registration_defaults("hubspot")
    assert defaults is not None
    assert defaults["serverUrl"] == "https://mcp.hubspot.com"
    assert defaults["authorizationUrl"] == "https://mcp.hubspot.com/oauth/authorize/user"
    assert defaults["tokenUrl"] == "https://mcp.hubspot.com/oauth/v3/token"
    assert defaults["pkce"] is True
    assert "managedConnectorMigration" not in defaults
