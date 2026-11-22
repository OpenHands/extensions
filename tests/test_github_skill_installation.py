"""Verify shared support is included in independently installed skills."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from openhands.sdk.skills import install_skill

ROOT = Path(__file__).resolve().parents[1]


def test_installed_comment_cleanup_skill_is_guide_only(tmp_path):
    name = "github-comment-cleanup"
    install_skill(source=str(ROOT / "skills" / name), installed_dir=tmp_path)
    installed = tmp_path / name

    assert (installed / "SKILL.md").is_file()
    assert not (installed / "scripts").exists()
    assert f"plugins/{name}" in (installed / "SKILL.md").read_text()


def test_comment_cleanup_plugin_manifest_and_entrypoint_exist():
    name = "github-comment-cleanup"
    manifest_path = ROOT / "plugins" / name / ".plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text())
    entrypoint = manifest["automation"]["entrypoint"]
    working_dir = ROOT / "plugins" / name / entrypoint.get("working_dir", ".")
    command_target = entrypoint["command"].split()[-1]

    assert manifest["automation"]["schema_version"] == "openhands.automation.plugin.v1"
    assert (working_dir / command_target).is_file()


def test_installed_triage_skill_contains_its_bundle(tmp_path):
    name = "github-issue-triage"
    install_skill(source=str(ROOT / "skills" / name), installed_dir=tmp_path)
    scripts = tmp_path / name / "scripts"
    manifest = json.loads(
        (ROOT / f"automations/catalog/{name}/manifest.json").read_text()
    )

    for filename, source in manifest["setup"]["bundle"]["files"].items():
        installed = scripts / filename
        assert installed.is_file() and not installed.is_symlink()
        assert installed.read_bytes() == (ROOT / source).read_bytes()

    result = subprocess.run(
        [sys.executable, "-c", "import worker"],
        cwd=scripts,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "name",
    [
        "github-repo-monitor",
        "github-agents-md-maintainer",
        "github-issue-to-pr",
        "github-pr-reviewer",
    ],
)
def test_installed_github_skill_contains_shared_client(tmp_path, name):
    install_skill(source=str(ROOT / "skills" / name), installed_dir=tmp_path)
    scripts = tmp_path / name / "scripts"
    helper = scripts / "github_client.py"

    assert helper.is_file() and not helper.is_symlink()
    assert (
        helper.read_bytes()
        == (ROOT / "skills/github/scripts/github_client.py").read_bytes()
    )
    result = subprocess.run(
        [sys.executable, "-c", "import main"],
        cwd=scripts,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
