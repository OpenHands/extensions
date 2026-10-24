"""The prompt-task plugin backs prompt automations created as plugin specs."""

import json
import re
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).parent.parent
PLUGIN = REPO_ROOT / "plugins" / "prompt-task"


def _automation() -> dict:
    return json.loads((PLUGIN / ".plugin" / "plugin.json").read_text())["automation"]


def test_runs_the_configured_prompt_on_a_chosen_agent_profile():
    automation = _automation()
    entrypoint = automation["entrypoint"]

    assert automation["schema_version"] == "openhands.automation.plugin.v1"
    assert entrypoint["runner"] == "conversation"
    assert (PLUGIN / "commands" / f"{entrypoint['command']}.md").is_file()
    assert entrypoint["arguments"] == "{{ config.prompt }}"
    assert automation["config_schema"]["required"] == ["prompt"]
    assert automation["runtime"]["agent_profile"] == {"required": True}


def test_command_triggers_no_public_skill():
    message = "/prompt-task:run "
    matches = []
    for skill in [
        *REPO_ROOT.glob("skills/*/SKILL.md"),
        *REPO_ROOT.glob("plugins/*/SKILL.md"),
        *REPO_ROOT.glob("plugins/*/skills/*/SKILL.md"),
    ]:
        frontmatter = re.match(r"^---\n(.*?)\n---", skill.read_text(), re.S)
        if not frontmatter:
            continue
        for trigger in (yaml.safe_load(frontmatter.group(1)) or {}).get(
            "triggers"
        ) or []:
            if str(trigger).lower() in message:
                matches.append(f"{skill.parent.name}: {trigger}")
    assert matches == []
