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


def test_catalog_ids_are_unique_and_automations_reference_existing_mcps():
    mcps = load_catalog_entries("mcps/catalog")
    automations = load_catalog_entries("automations/catalog")

    mcp_ids = [entry["id"] for entry in mcps]
    automation_ids = [entry["id"] for entry in automations]

    assert len(mcp_ids) == len(set(mcp_ids))
    assert len(automation_ids) == len(set(automation_ids))

    known_mcp_ids = set(mcp_ids)
    for automation in automations:
        assert automation["requiredMcpIds"]
        missing_ids = set(automation["requiredMcpIds"]) - known_mcp_ids
        assert missing_ids == set()


def test_catalog_entries_have_required_fields():
    for entry in load_catalog_entries("mcps/catalog"):
        assert entry["id"]
        assert entry["name"]
        assert entry["description"]
        assert entry["iconBg"]
        assert entry["template"]["kind"] in {"stdio", "shttp", "sse"}
        if entry["template"]["kind"] == "stdio":
            assert entry["template"]["serverName"]
            assert entry["template"]["command"]
            assert isinstance(entry["template"]["args"], list)
        else:
            assert entry["template"]["url"].startswith("https://")

    for entry in load_catalog_entries("automations/catalog"):
        assert entry["id"]
        assert entry["name"]
        assert entry["prompt"]
        assert entry["exampleImplementation"]
        assert isinstance(entry["popularityRank"], int)
        assert isinstance(entry["estimatedSetupMinutes"], int)


def test_node_package_exports_catalogs():
    script = """
      import { MCP_CATALOG, AUTOMATION_CATALOG } from './index.js';
      if (!Array.isArray(MCP_CATALOG) || MCP_CATALOG.length === 0) process.exit(1);
      if (!Array.isArray(AUTOMATION_CATALOG) || AUTOMATION_CATALOG.length === 0) process.exit(1);
      if (!MCP_CATALOG.some((entry) => entry.id === 'github')) process.exit(1);
      if (!AUTOMATION_CATALOG.some((entry) => entry.id === 'github-pr-reviewer')) process.exit(1);
    """
    subprocess.run(["node", "--input-type=module", "-e", script], cwd=ROOT, check=True)
