"""Assert integration catalog files drive the generated JS/Python assets."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import openhands_extensions
import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "integrations" / "catalog"
CATALOG_INDEX = ROOT / "integrations" / "catalog-index.js"
AGGREGATE_ASSETS = [
    ROOT / "integrations" / "integration-catalog.json",
    ROOT / "python" / "openhands_extensions" / "integration-catalog.json",
]


def _catalog_files() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text()) for p in CATALOG_DIR.glob("*.json")}


def _catalog_entries() -> list[dict]:
    entries = list(_catalog_files().values())
    return sorted(entries, key=lambda entry: (-(entry.get("popularityRank") if entry.get("popularityRank") is not None else -1), entry["id"]))


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
        assert "availability" not in entry
        assert "runtimeAvailability" not in entry


def test_no_aggregate_catalog_json_exists() -> None:
    for asset in AGGREGATE_ASSETS:
        assert not asset.exists()


def test_generated_js_index_references_catalog_directory() -> None:
    body = CATALOG_INDEX.read_text()
    for file in sorted(path.name for path in CATALOG_DIR.glob("*.json")):
        assert f"./catalog/{file}" in body
    assert "integration-catalog.json" not in body


def test_python_snapshot_is_built_from_catalog_directory() -> None:
    assert openhands_extensions.INTEGRATION_CATALOG_SNAPSHOT == {
        "integrations": _catalog_entries()
    }


def test_python_list_integration_catalog_returns_raw_entries() -> None:
    entries = openhands_extensions.list_integration_catalog()
    assert entries == _catalog_entries()
    for entry in entries:
        assert "supportsMcp" not in entry
        assert "supportsOauth" not in entry
        assert "registrationDefaults" not in entry
        assert "managedConnectorSlug" not in entry
        assert "authStrategy" not in entry
        assert "defaultConnectionOptionId" not in entry
        assert "catalogStatus" not in entry
        assert "availability" not in entry
        assert "runtimeAvailability" not in entry


def test_python_list_integration_catalog_models_returns_typed_entries() -> None:
    entries = openhands_extensions.list_integration_catalog()
    models = openhands_extensions.list_integration_catalog_models()

    assert [model.model_dump(exclude_none=True) for model in models] == entries
    assert all(
        isinstance(model, openhands_extensions.IntegrationCatalogEntry)
        for model in models
    )
    assert (
        openhands_extensions.get_integration_catalog_entry_model(entries[0]["id"])
        == models[0]
    )
    assert openhands_extensions.get_integration_catalog_entry_model("missing") is None

    with pytest.raises(ValidationError):
        openhands_extensions.IntegrationCatalogEntry.model_validate(
            {**entries[0], "unexpected": True}
        )


def test_logo_metadata_is_serializable_and_language_agnostic() -> None:
    entries = openhands_extensions.list_integration_catalog()
    with_logo = [entry for entry in entries if entry.get("logoUrl")]
    assert with_logo
    assert any(entry["id"].startswith("cloudflare-") for entry in with_logo)
    for entry in with_logo:
        assert isinstance(entry["logoUrl"], str)
        assert entry["logoUrl"].startswith("https://")
        assert "react" not in entry["logoUrl"].lower()


def test_get_integration_catalog_entry_round_trip() -> None:
    sample_id = openhands_extensions.list_integration_catalog()[0]["id"]
    sample = openhands_extensions.get_integration_catalog_entry(sample_id)
    assert sample is not None
    assert sample == next(
        entry
        for entry in openhands_extensions.list_integration_catalog()
        if entry["id"] == sample_id
    )
    assert openhands_extensions.get_integration_catalog_entry("nope") is None


def _js_call(expr: str) -> str:
    result = subprocess.run(
        ["node", "--input-type=module", "-e", expr],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    return result.stdout


def test_js_reads_the_same_catalog_as_python() -> None:
    integrations = _js_call(
        "import { listIntegrationCatalog } from './integrations/index.js';\n"
        "process.stdout.write(JSON.stringify(listIntegrationCatalog()));"
    )
    assert json.loads(integrations) == openhands_extensions.list_integration_catalog()

    sample_id = openhands_extensions.list_integration_catalog()[0]["id"]
    sample = _js_call(
        "import { getIntegrationCatalogEntry } from './integrations/index.js';\n"
        f"process.stdout.write(JSON.stringify(getIntegrationCatalogEntry({json.dumps(sample_id)})));"
    )
    assert json.loads(sample) == openhands_extensions.get_integration_catalog_entry(sample_id)


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
    all_mcp = {
        e["id"]
        for e in openhands_extensions.list_integration_catalog()
        if _supports_mcp(e)
    }
    assert py_ids == js_ids == all_mcp
    assert "filesystem" in py_ids


def test_filter_oauth_only() -> None:
    py_ids = {e["id"] for e in openhands_extensions.list_integration_catalog(oauth=True)}
    js_ids = set(_js_filter("undefined", "true"))
    all_oauth = {
        e["id"]
        for e in openhands_extensions.list_integration_catalog()
        if _supports_oauth(e)
    }
    assert py_ids == js_ids == all_oauth
    assert py_ids


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

    sample_id = openhands_extensions.list_integration_catalog()[0]["id"]
    sample = openhands_extensions.get_integration_catalog_entry(sample_id)
    assert sample is not None
    sample["__mutated"] = True
    assert "__mutated" not in openhands_extensions.get_integration_catalog_entry(sample_id)

    snapshot = openhands_extensions.INTEGRATION_CATALOG_SNAPSHOT
    snapshot["integrations"][0]["__mutated"] = True
    assert "__mutated" not in openhands_extensions.list_integration_catalog()[0]


def test_js_accessors_return_independent_copies() -> None:
    sample_id = openhands_extensions.list_integration_catalog()[0]["id"]
    expr = f"""
        import {{
          INTEGRATION_CATALOG,
          getIntegrationCatalogEntry,
          listIntegrationCatalog,
        }} from './integrations/index.js';
        const sampleId = {json.dumps(sample_id)};
        const first = listIntegrationCatalog();
        const second = listIntegrationCatalog();
        first[0].__mutated = true;
        const entry = getIntegrationCatalogEntry(sampleId);
        entry.__mutated = true;
        INTEGRATION_CATALOG[0].__mutated = true;
        process.stdout.write(JSON.stringify({{
          listsAreIndependent:
            !('__mutated' in second[0]) &&
            !('__mutated' in listIntegrationCatalog()[0]),
          entryIsIndependent: !('__mutated' in getIntegrationCatalogEntry(sampleId)),
        }}));
    """
    result = json.loads(_js_call(expr))
    assert result == {"listsAreIndependent": True, "entryIsIndependent": True}


def test_oauth_config_lives_on_connection_options() -> None:
    oauth_entries = [
        entry
        for entry in openhands_extensions.list_integration_catalog()
        if _supports_oauth(entry)
    ]
    assert oauth_entries
    for entry in oauth_entries:
        assert "registrationDefaults" not in entry
        oauth_options = [
            option
            for option in entry["connectionOptions"]
            if option.get("auth", {}).get("strategy") == "oauth2"
        ]
        assert oauth_options
        for option in oauth_options:
            assert "registrationDefaults" not in option
            oauth = option["auth"].get("oauth")
            if oauth is not None:
                assert isinstance(oauth, dict)
