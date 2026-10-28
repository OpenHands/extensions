import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANIFESTS = sorted((ROOT / "plugins").glob("*/.plugin/plugin.json"))


def _automation_manifests():
    for manifest_path in PLUGIN_MANIFESTS:
        data = json.loads(manifest_path.read_text())
        automation = data.get("automation")
        if automation:
            yield manifest_path, data, automation


def test_automation_plugin_manifests_have_valid_entrypoints():
    manifests = list(_automation_manifests())
    assert manifests, "No automation plugin manifests found"

    for manifest_path, data, automation in manifests:
        plugin_root = manifest_path.parents[1]
        assert automation["schema_version"] == "openhands.automation.plugin.v1"
        assert data["name"] == plugin_root.name

        entrypoint = automation["entrypoint"]
        assert entrypoint["runner"] == "script"
        working_dir = plugin_root / entrypoint.get("working_dir", ".")
        assert working_dir.is_dir(), f"{data['name']}: missing working_dir"

        command_parts = entrypoint["command"].split()
        assert command_parts[:2] == ["python3", "plugin_runner.py"]
        assert (working_dir / "plugin_runner.py").is_file()
        assert len(command_parts) == 3
        assert (working_dir / command_parts[2]).is_file(), (
            f"{data['name']}: entrypoint target is missing"
        )


def test_automation_plugin_config_schemas_are_objects():
    for _manifest_path, data, automation in _automation_manifests():
        schema = automation.get("config_schema") or {}
        assert schema.get("type") == "object", data["name"]
        assert schema.get("additionalProperties") is False, data["name"]
        assert isinstance(schema.get("properties"), dict), data["name"]


def test_catalog_bundle_files_are_sourced_from_plugins():
    for manifest_path in sorted((ROOT / "automations" / "catalog").glob("*/manifest.json")):
        entry = json.loads(manifest_path.read_text())
        files = entry.get("setup", {}).get("bundle", {}).get("files", {})
        for packed_path, source in files.items():
            assert source.startswith("plugins/"), (
                f"{entry['id']} bundle file {packed_path} still sources {source}"
            )
            assert (ROOT / source).is_file(), source
