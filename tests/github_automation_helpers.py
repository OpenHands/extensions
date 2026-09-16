"""Exercise the actual shipped entrypoints with mocked GitHub/SDK boundaries."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def worker(name, tmp_path, monkeypatch):
    manifest = json.loads(
        (ROOT / f"automations/catalog/{name}/manifest.json").read_text()
    )
    bundle = tmp_path / name
    bundle.mkdir()
    for filename, source in manifest["setup"]["bundle"]["files"].items():
        (bundle / filename).write_text((ROOT / source).read_text())
    for module in (
        "agent_conversation",
        "main",
        "github_client",
        "qa_prompt",
        "worker",
    ):
        monkeypatch.delitem(sys.modules, module, raising=False)
    monkeypatch.syspath_prepend(str(bundle))
    spec = importlib.util.spec_from_file_location("worker", bundle / "worker.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
