"""Assert integration catalog files drive the generated JS/Python assets."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import openhands_extensions

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "integrations" / "integration-catalog.json"
CATALOG_DIR = ROOT / "integrations" / "catalog"


def _catalog_files() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text()) for p in CATALOG_DIR.glob("*.json")}


def _generated_asset() -> dict:
    return json.loads(ASSET.read_text())


def _supports_mcp(entry: dict) -> bool:
    return any(option.get("provider") == "mcp" for option in entry["connectionOptions"])


def _supports_oauth(entry: dict) -> bool:
    return any(option.get("auth", {}).get("strategy") == "oauth2" for option in entry["connectionOptions"])



def test_catalog_directory_is_hand_authored_source_of_truth() -> None:
    for integration_id, entry in _catalog_files().items():
        assert entry["id"] == integration_id
        assert "supportsMcp" not in entry
        assert "supportsOauth" not in entry
        assert "oauthProvider" not in entry
        assert "registrationDefaults" not in entry
        assert "managedConnectorSlug" not in entry
        assert "authStrategy" not in entry
        assert "defaultConnectionOptionId" not in entry
        assert "kind" not in entry
        assert "catalogStatus" not in entry


def test_generated_asset_matches_catalog_directory() -> None:
    generated = _generated_asset()
    assert set(generated.keys()) == {"integrations"}
    master = {e["id"]: e for e in generated["integrations"]}
    catalog_files = _catalog_files()
    assert set(catalog_files) == set(master)
    for integration_id, entry in master.items():
        assert catalog_files[integration_id] == entry


def test_python_reads_the_same_asset() -> None:
    assert openhands_extensions.INTEGRATION_CATALOG_SNAPSHOT == json.loads(ASSET.read_text())


def test_python_list_integration_catalog_returns_raw_entries() -> None:
    entries = openhands_extensions.list_integration_catalog()
    assert entries == _generated_asset()["integrations"]
    for entry in entries:
        assert "supportsMcp" not in entry
        assert "supportsOauth" not in entry
        assert "registrationDefaults" not in entry
        assert "managedConnectorSlug" not in entry
        assert "authStrategy" not in entry
        assert "defaultConnectionOptionId" not in entry
        assert "catalogStatus" not in entry


def test_get_integration_catalog_entry_round_trip() -> None:
    github = openhands_extensions.get_integration_catalog_entry("github")
    assert github is not None
    assert github == next(
        entry for entry in openhands_extensions.list_integration_catalog() if entry["id"] == "github"
    )
    assert openhands_extensions.get_integration_catalog_entry("nope") is None


def test_python_asset_is_byte_identical_to_root_asset() -> None:
    root_asset = ASSET.read_bytes()
    py_asset = (ROOT / "python" / "openhands_extensions" / "integration-catalog.json").read_bytes()
    assert root_asset == py_asset


def _js_call(expr: str) -> str:
    result = subprocess.run(
        ["node", "--input-type=module", "-e", expr],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    return result.stdout


def test_js_reads_the_same_asset_as_python() -> None:
    integrations = _js_call(
        "import { listIntegrationCatalog } from './integrations/index.js';\n"
        "process.stdout.write(JSON.stringify(listIntegrationCatalog()));"
    )
    assert json.loads(integrations) == openhands_extensions.list_integration_catalog()

    github = _js_call(
        "import { getIntegrationCatalogEntry } from './integrations/index.js';\n"
        "process.stdout.write(JSON.stringify(getIntegrationCatalogEntry('github')));"
    )
    assert json.loads(github) == openhands_extensions.get_integration_catalog_entry("github")


def _js_filter(mcp, oauth) -> list[str]:
    expr = (
        "import { listIntegrationCatalog } from './integrations/index.js';\n"
        f"const f = listIntegrationCatalog({{ mcp: {mcp}, oauth: {oauth} }});\n"
        "process.stdout.write(JSON.stringify(f.map((e) => e.id)));"
    )
    return json.loads(_js_call(expr))


def test_filter_mcp_only() -> None:
    py_ids = {e["id"] for e in openhands_extensions.list_integration_catalog(mcp=True)}
    js_ids = set(_js_filter("true", "undefined"))
    all_mcp = {e["id"] for e in openhands_extensions.list_integration_catalog() if _supports_mcp(e)}
    assert py_ids == js_ids == all_mcp
    assert "filesystem" in py_ids


def test_filter_oauth_only() -> None:
    py_ids = {e["id"] for e in openhands_extensions.list_integration_catalog(oauth=True)}
    js_ids = set(_js_filter("undefined", "true"))
    all_oauth = {e["id"] for e in openhands_extensions.list_integration_catalog() if _supports_oauth(e)}
    assert py_ids == js_ids == all_oauth
    assert "github" in py_ids


def test_filter_oauth_not_mcp() -> None:
    py_ids = {
        e["id"] for e in openhands_extensions.list_integration_catalog(oauth=True, mcp=False)
    }
    js_ids = set(_js_filter("false", "true"))
    expected = {
        e["id"]
        for e in openhands_extensions.list_integration_catalog()
        if _supports_oauth(e) and not _supports_mcp(e)
    }
    assert py_ids == js_ids == expected


def test_filter_none_returns_all() -> None:
    assert len(openhands_extensions.list_integration_catalog()) == len(
        openhands_extensions.list_integration_catalog(mcp=None, oauth=None)
    )


def test_accessors_return_independent_copies() -> None:
    catalog_a = openhands_extensions.list_integration_catalog()
    catalog_b = openhands_extensions.list_integration_catalog()
    assert catalog_a == catalog_b
    assert catalog_a is not catalog_b
    catalog_a[0]["__mutated"] = True
    assert "__mutated" not in openhands_extensions.list_integration_catalog()[0]

    github = openhands_extensions.get_integration_catalog_entry("github")
    assert github is not None
    github["__mutated"] = True
    assert "__mutated" not in openhands_extensions.get_integration_catalog_entry("github")

    snapshot = openhands_extensions.INTEGRATION_CATALOG_SNAPSHOT
    snapshot["integrations"][0]["__mutated"] = True
    assert "__mutated" not in openhands_extensions.list_integration_catalog()[0]


def test_hubspot_oauth_config_lives_on_connection_option() -> None:
    hubspot = openhands_extensions.get_integration_catalog_entry("hubspot")
    assert hubspot is not None
    assert "registrationDefaults" not in hubspot
    option = hubspot["connectionOptions"][0]
    assert option["provider"] == "mcp"
    assert option["transport"]["url"] == "https://mcp.hubspot.com"
    oauth = option["auth"]["oauth"]
    assert oauth["authorizationUrl"] == "https://mcp.hubspot.com/oauth/authorize/user"
    assert oauth["tokenUrl"] == "https://mcp.hubspot.com/oauth/v3/token"
    assert oauth["pkce"] is True
