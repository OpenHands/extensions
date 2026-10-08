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
