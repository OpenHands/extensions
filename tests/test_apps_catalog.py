import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_apps_catalog_is_valid_and_package_export_matches():
    entries = json.loads((ROOT / "apps/catalog.json").read_text())
    assert isinstance(entries, list)
    assert len({entry["id"] for entry in entries}) == len(entries)
    for entry in entries:
        assert set(entry) == {"id", "name", "description", "source", "manifest", "beta"}
        assert entry["id"] and entry["source"].startswith("./apps/")
        assert entry["manifest"].endswith("/canvas-extension.json")
        assert entry["beta"] is True
    subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            "import { APPS_CATALOG } from './index.js'; if (!Array.isArray(APPS_CATALOG)) process.exit(1)",
        ],
        cwd=ROOT,
        check=True,
    )


def test_kanban_catalog_preserves_installation_identity():
    entries = json.loads((ROOT / "apps/catalog.json").read_text())
    entry = next(entry for entry in entries if entry["id"] == "kanban-manager")
    assert entry["beta"] is True
    source = ROOT / entry["source"].removeprefix("./")
    manifest = json.loads((ROOT / entry["manifest"].removeprefix("./")).read_text())
    assert manifest["name"] == "kanban-manager"
    assert manifest["contributes"]["pages"][0]["id"] == "board"
    assert (source / manifest["entrypoint"]).is_file()
    assert (source / "LICENSE").is_file()


def test_every_app_directory_is_catalogued_with_a_matching_manifest():
    entries = json.loads((ROOT / "apps/catalog.json").read_text())
    by_id = {entry["id"]: entry for entry in entries}
    app_dirs = sorted(p.name for p in (ROOT / "apps").iterdir() if (p / "canvas-extension.json").is_file())
    assert sorted(by_id) == app_dirs
    for app_id, entry in by_id.items():
        source = ROOT / entry["source"].removeprefix("./")
        manifest = json.loads((ROOT / entry["manifest"].removeprefix("./")).read_text())
        assert source == ROOT / "apps" / app_id
        assert manifest["name"] == app_id
        assert entry["name"] == manifest["display_name"]
        assert (source / manifest["entrypoint"]).is_file()
        assert (source / "README.md").is_file()


def test_apps_moved_from_canvas_apps_keep_their_license_and_source():
    moved = [
        "agent-memory-viewer", "backend-sqlite-studio", "browser-sql-lab", "canvas-pulse",
        "conversation-search-sidecar", "conversation-trace", "extension-lab", "git-cockpit",
        "kanban-manager", "personal-profile", "snake-arcade", "terminal", "usage-insights",
        "vite-showcase", "wasm-repo-lens",
    ]
    for app_id in moved:
        app = ROOT / "apps" / app_id
        assert (app / "LICENSE").is_file(), app_id
        assert "github.com/OpenHands/canvas-apps/tree/" in (app / "README.md").read_text(), app_id
