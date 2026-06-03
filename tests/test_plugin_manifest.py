"""Test that all plugin.json manifests are valid and Claude Code compatible."""

import json
from pathlib import Path

import pytest


def get_plugins_directory():
    """Get the path to the plugins directory."""
    test_dir = Path(__file__).parent
    return test_dir.parent / "plugins"


def get_all_plugin_manifests():
    """Yield (plugin_name, manifest_path) for every plugin with a .plugin/plugin.json."""
    plugins_dir = get_plugins_directory()
    for plugin_dir in sorted(plugins_dir.iterdir()):
        if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
            continue
        manifest = plugin_dir / ".plugin" / "plugin.json"
        if manifest.exists():
            yield plugin_dir.name, manifest


REQUIRED_FIELDS = ["name", "description", "author", "version"]


@pytest.fixture(params=list(get_all_plugin_manifests()), ids=lambda p: p[0])
def plugin_manifest(request):
    """Parametrized fixture returning (name, path, parsed_json) for each plugin."""
    name, path = request.param
    data = json.loads(path.read_text())
    return name, path, data


def test_plugin_has_required_fields(plugin_manifest):
    name, path, data = plugin_manifest
    for field in REQUIRED_FIELDS:
        assert field in data, (
            f"Plugin '{name}' is missing required field '{field}' in {path}"
        )


def test_plugin_author_is_object(plugin_manifest):
    """Claude Code requires 'author' to be an object with at least a 'name' key."""
    name, path, data = plugin_manifest
    author = data.get("author")
    assert isinstance(author, dict), (
        f"Plugin '{name}': 'author' must be an object (got {type(author).__name__}). "
        f"Use {{\"name\": \"...\", \"email\": \"...\"}} format for Claude Code compatibility."
    )
    assert "name" in author, (
        f"Plugin '{name}': 'author' object must contain a 'name' field."
    )


def test_plugin_json_is_valid(plugin_manifest):
    """Ensure plugin.json is valid JSON with expected types."""
    name, path, data = plugin_manifest
    assert isinstance(data.get("name"), str), f"Plugin '{name}': 'name' must be a string"
    assert isinstance(data.get("version"), str), f"Plugin '{name}': 'version' must be a string"
    assert isinstance(data.get("description"), str), f"Plugin '{name}': 'description' must be a string"


def test_all_plugins_have_manifest():
    """Ensure every plugin directory has a .plugin/plugin.json manifest."""
    plugins_dir = get_plugins_directory()
    plugin_dirs = [
        d.name
        for d in plugins_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]
    assert len(plugin_dirs) > 0, "No plugin directories found"

    missing = [
        name
        for name in plugin_dirs
        if not (plugins_dir / name / ".plugin" / "plugin.json").exists()
    ]
    assert len(missing) == 0, (
        f"Plugins missing .plugin/plugin.json: {', '.join(missing)}"
    )
