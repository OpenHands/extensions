import json
import re
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
    """All password fields must have helperText plus a link (either a helperLink field or a
    markdown link embedded in helperText) so users know how to get credentials."""
    markdown_link_re = re.compile(r"\[.+?\]\(https://[^)]+\)")

    for entry in load_catalog_entries("integrations/catalog"):
        for option in entry["connectionOptions"]:
            transport = option.get("transport", {})
            for field_group in ("envFields", "argFields"):
                for field in transport.get(field_group, []):
                    if field.get("type") == "password":
                        field_key = field.get("key", "<unknown>")
                        assert "helperText" in field, (
                            f"{entry['id']}: password field '{field_key}' is missing helperText"
                        )
                        assert field["helperText"], (
                            f"{entry['id']}: password field '{field_key}' has empty helperText"
                        )
                        has_helper_link = field.get("helperLink", "").startswith("https://")
                        has_inline_link = bool(markdown_link_re.search(field["helperText"]))
                        assert has_helper_link or has_inline_link, (
                            f"{entry['id']}: password field '{field_key}' must have a helperLink "
                            f"or a markdown link in helperText"
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


def test_managed_connector_migration_descriptors_are_well_formed():
    """Every provider that declares a managed-connector migration descriptor
    must do so declaratively on its catalog entry (no provider-specific named
    exports). The descriptor is consumed generically by the integrations hub, so
    this asserts structural invariants that hold for ANY provider:

      - canonicalServerUrl is a non-empty https URL
      - legacyScopeBundles has all four bundles as string arrays
      - union equals required + optional (order-preserving)
      - unionWithoutOauth equals union with the "oauth" scope removed
      - errorHints is declared alongside the migration

    This is intentionally provider-agnostic: it never references a slug or any
    provider-named symbol.
    """
    script = r"""
      import { listOAuthProviderCatalog } from './integrations/index.js';

      const isStringArray = (v) => Array.isArray(v) && v.every((s) => typeof s === 'string');
      const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

      let declared = 0;
      for (const provider of listOAuthProviderCatalog()) {
        const migration = provider.registrationDefaults?.managedConnectorMigration;
        if (!migration) continue;
        declared += 1;

        if (!/^https:\/\//.test(migration.canonicalServerUrl)) {
          console.error('canonicalServerUrl must be an https URL');
          process.exit(1);
        }
        const bundles = migration.legacyScopeBundles;
        for (const key of ['required', 'optional', 'union', 'unionWithoutOauth']) {
          if (!isStringArray(bundles[key])) {
            console.error(`legacyScopeBundles.${key} must be a string array`);
            process.exit(1);
          }
        }
        const expectedUnion = [...bundles.required, ...bundles.optional];
        if (!eq(bundles.union, expectedUnion)) {
          console.error('union must equal required + optional');
          process.exit(1);
        }
        const expectedUnionWithoutOauth = expectedUnion.filter((s) => s !== 'oauth');
        if (!eq(bundles.unionWithoutOauth, expectedUnionWithoutOauth)) {
          console.error('unionWithoutOauth must equal union minus "oauth"');
          process.exit(1);
        }
        const errorHints = provider.registrationDefaults?.errorHints;
        if (!errorHints || typeof errorHints !== 'object') {
          console.error('errorHints must be declared alongside managedConnectorMigration');
          process.exit(1);
        }
      }
      if (declared === 0) {
        console.error('expected at least one provider to declare a managedConnectorMigration');
        process.exit(1);
      }
    """
    subprocess.run(["node", "--input-type=module", "-e", script], cwd=ROOT, check=True)
