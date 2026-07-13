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
        # iconBg/iconColor are optional UI styling hints (OAuth-only entries may
        # ship without a bespoke icon background).
        assert "iconBg" not in entry or entry["iconBg"]
        assert entry["connectionOptions"]
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


def test_remote_no_auth_mcp_entries_are_intentionally_public():
    public_remote_mcp_ids = {"cloudflare-docs", "deepwiki", "huggingface"}

    actual = set()
    for entry in load_catalog_entries("integrations/catalog"):
        for option in entry["connectionOptions"]:
            transport = option.get("transport", {})
            # An option with `headerFields` still requires the user to supply
            # credentials (just via named headers, e.g. Datadog's
            # DD_API_KEY/DD_APPLICATION_KEY), so it is NOT "public/no-auth".
            has_header_credentials = bool(transport.get("headerFields"))
            if (
                option["provider"] == "mcp"
                and option["auth"]["strategy"] == "none"
                and not has_header_credentials
                and transport.get("url", "").startswith("https://")
            ):
                actual.add(entry["id"])
                assert transport["kind"] == "shttp"

    assert actual == public_remote_mcp_ids


def test_datadog_mcp_uses_documented_api_key_headers():
    datadog = next(
        entry
        for entry in load_catalog_entries("integrations/catalog")
        if entry["id"] == "datadog"
    )
    api_option = next(
        option for option in datadog["connectionOptions"] if option["id"] == "api"
    )

    assert [
        field["key"] for field in api_option["transport"]["headerFields"]
    ] == ["DD_API_KEY", "DD_APPLICATION_KEY"]


def test_credential_fields_have_helper_text_and_link():
    """All password fields must have helperText plus a link (either a helperLink field or a
    markdown link embedded in helperText) so users know how to get credentials."""
    markdown_link_re = re.compile(r"\[.+?\]\(https://[^)]+\)")

    for entry in load_catalog_entries("integrations/catalog"):
        for option in entry["connectionOptions"]:
            transport = option.get("transport", {})
            for field_group in ("envFields", "argFields", "headerFields"):
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


def test_no_default_tool_in_catalog():
    """The defaultTool field was removed; tools now come from MCP tools/list or
    HTTP OpenAPI regeneration. No connection option may carry it."""
    offenders = []
    for entry in load_catalog_entries("integrations/catalog"):
        for option in entry["connectionOptions"]:
            http_cfg = option.get("http", {})
            if "defaultTool" in http_cfg:
                offenders.append(f"{entry['id']}.{option['id']}")
    assert not offenders, f"defaultTool still present in: {offenders}"


def test_http_connectors_have_openapi_url():
    """An HTTP connector without an openApiUrl has no tool-discovery path once
    defaultTool is gone, so every HTTP option must ship an openApiUrl."""
    offenders = []
    for entry in load_catalog_entries("integrations/catalog"):
        for option in entry["connectionOptions"]:
            if option["provider"] == "http":
                http_cfg = option.get("http", {})
                url = http_cfg.get("openApiUrl")
                if not url or not url.startswith("https://"):
                    offenders.append(f"{entry['id']}.{option['id']}")
    assert not offenders, f"HTTP options missing openApiUrl: {offenders}"
