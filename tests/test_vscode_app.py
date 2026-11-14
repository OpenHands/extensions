import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "vscode"


def test_vscode_app_manifest_has_pinned_remote_dual_arch_artifacts():
    manifest = json.loads((APP / "canvas-extension.json").read_text())
    backend = manifest["backend"]
    assert set(backend["artifacts"]) == {"linux-amd64", "linux-arm64"}
    for artifact in backend["artifacts"].values():
        assert artifact["url"].startswith(
            "https://github.com/gitpod-io/openvscode-server/releases/download/"
        )
        assert artifact["url"].endswith(".tar.gz")
        assert len(artifact["sha256"]) == 64
        assert artifact["strip_components"] == 1
        assert "path" not in artifact
    assert backend["argv"][0] == "{artifact_dir}/bin/openvscode-server"
    assert "HOME" not in backend["inherit_environment"]
    assert manifest["entrypoint"] == "extension.js"


def test_ready_entrypoint_is_self_contained_and_full_height():
    source = (APP / "extension.js").read_text()
    assert "export function activate" in source
    assert "host.appBackendView.mount" in source
    assert "query: { folder }" in source
    assert "localStorage" in source
    assert "height:100vh" in source
    assert "<iframe" not in source
    assert "import " not in source
    subprocess.run(["node", "--check", str(APP / "extension.js")], check=True)


def test_release_binaries_are_not_committed():
    assert not list(APP.glob("backend/*"))
