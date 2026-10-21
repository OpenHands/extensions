"""Verify automation skills delegate runtime code to plugins."""

import json
from pathlib import Path

import pytest
from openhands.sdk.skills import install_skill

ROOT = Path(__file__).resolve().parents[1]
AUTOMATION_PLUGIN_SKILLS = [
    "github-repo-monitor",
    "github-agents-md-maintainer",
    "github-issue-to-pr",
    "github-issue-triage",
    "github-pr-reviewer",
    "github-stale-ci-pr-closer",
    "gitlab-issue-to-mr",
    "jira-issue-to-pr",
    "news-digest",
    "slack-channel-monitor",
]


@pytest.mark.parametrize("name", AUTOMATION_PLUGIN_SKILLS)
def test_installed_automation_skill_is_guide_only(tmp_path, name):
    install_skill(source=str(ROOT / "skills" / name), installed_dir=tmp_path)
    installed = tmp_path / name

    assert (installed / "SKILL.md").is_file()
    assert not (installed / "scripts").exists()
    assert f"plugins/{name}" in (installed / "SKILL.md").read_text()


@pytest.mark.parametrize("name", AUTOMATION_PLUGIN_SKILLS)
def test_automation_plugin_manifest_and_entrypoint_exist(name):
    manifest_path = ROOT / "plugins" / name / ".plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text())
    entrypoint = manifest["automation"]["entrypoint"]
    working_dir = ROOT / "plugins" / name / entrypoint.get("working_dir", ".")
    command_target = entrypoint["command"].split()[-1]

    assert manifest["automation"]["schema_version"] == "openhands.automation.plugin.v1"
    assert (working_dir / command_target).is_file()
