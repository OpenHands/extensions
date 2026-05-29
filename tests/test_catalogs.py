import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_catalog_entries(relative_path: str):
    entries = []
    for entry_path in sorted((ROOT / relative_path).glob("*.json")):
        entry = json.loads(entry_path.read_text())
        assert entry["id"] == entry_path.stem
        entries.append(entry)
    return entries


def test_catalog_ids_are_unique_and_automations_reference_existing_integrations():
    integrations = load_catalog_entries("integrations/catalog")
    automations = load_catalog_entries("automations/catalog")

    integration_ids = [entry["id"] for entry in integrations]
    automation_ids = [entry["id"] for entry in automations]

    assert len(integration_ids) == len(set(integration_ids))
    assert len(automation_ids) == len(set(automation_ids))

    known_integration_ids = set(integration_ids)
    for automation in automations:
        assert automation["requiredIntegrationIds"]
        missing_ids = (
            set(automation["requiredIntegrationIds"]) - known_integration_ids
        )
        assert missing_ids == set()


def test_catalog_entries_have_required_fields():
    for entry in load_catalog_entries("integrations/catalog"):
        assert entry["id"]
        assert entry["name"]
        assert entry["description"]
        assert entry["kind"] in {"mcp", "http"}
        assert entry["iconBg"]
        assert entry["connectionOptions"]
        assert entry["defaultConnectionOptionId"]
        for option in entry["connectionOptions"]:
            assert option["id"]
            assert option["provider"] in {"mcp", "http"}
            assert option["auth"]["strategy"] in {
                "none",
                "api_key",
                "bearer",
                "basic",
                "oauth2",
            }
            if option["provider"] == "mcp":
                assert option["transport"]["kind"] in {"stdio", "shttp", "sse"}
                if option["transport"]["kind"] == "stdio":
                    assert option["transport"]["serverName"]
                    assert option["transport"]["command"]
                    assert isinstance(option["transport"]["args"], list)
                else:
                    assert option["transport"]["url"].startswith("https://")

    for entry in load_catalog_entries("automations/catalog"):
        assert entry["id"]
        assert entry["name"]
        assert entry["prompt"]
        assert entry["exampleImplementation"]
        assert isinstance(entry["popularityRank"], int)
        assert isinstance(entry["estimatedSetupMinutes"], int)


def test_credential_fields_have_helper_text_and_link():
    """All password fields must have helperText and helperLink so users know how to get credentials."""
    for entry in load_catalog_entries("integrations/catalog"):
        for option in entry["connectionOptions"]:
            transport = option.get("transport", {})
            for field_group in ("envFields", "argFields"):
                for field in transport.get(field_group, []):
                    if field.get("type") == "password":
                        assert "helperText" in field, (
                            f"{entry['id']}: password field '{field['key']}' is missing helperText"
                        )
                        assert "helperLink" in field, (
                            f"{entry['id']}: password field '{field['key']}' is missing helperLink"
                        )
                        assert field["helperText"], (
                            f"{entry['id']}: password field '{field['key']}' has empty helperText"
                        )
                        assert field["helperLink"].startswith("https://"), (
                            f"{entry['id']}: password field '{field['key']}' helperLink must start with https://"
                        )


def test_node_package_exports_catalogs():
    script = """
      import { INTEGRATION_CATALOG, AUTOMATION_CATALOG } from './index.js';
      if (!Array.isArray(INTEGRATION_CATALOG) || INTEGRATION_CATALOG.length === 0) process.exit(1);
      if (!Array.isArray(AUTOMATION_CATALOG) || AUTOMATION_CATALOG.length === 0) process.exit(1);
      if (!INTEGRATION_CATALOG.some((entry) => entry.id === 'github')) process.exit(1);
      if (!AUTOMATION_CATALOG.some((entry) => entry.id === 'github-pr-reviewer')) process.exit(1);
    """
    subprocess.run(["node", "--input-type=module", "-e", script], cwd=ROOT, check=True)
