"""The openhands-automation skill names the built-in event sources and keeps
an Agent Canvas setup session on its form.

The skill is keyword-triggered, so it also loads in the Agent Canvas automation
setup conversation. There it used to send the agent to the automation API, which
created and enabled automations before the user reviewed the form, and it called
GitHub the only built-in source, so Data Center requests got invented sources
and custom webhooks.
"""

import re
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).parent.parent / "skills" / "openhands-automation"
BUILT_IN_SOURCES = ("github", "jira_dc", "bitbucket_data_center", "azure_devops")


@pytest.fixture(scope="module")
def skill_text() -> str:
    return (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def readme_text() -> str:
    return (SKILL_DIR / "README.md").read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    match = re.search(rf"(?m)^(#+) {re.escape(heading)}\n", text)
    assert match, f"missing section {heading!r}"
    level = len(match.group(1))
    end = re.compile(rf"(?m)^#{{1,{level}}} ")
    following = end.search(text, match.end())
    return text[match.end() : following.start() if following else len(text)]


def test_lists_the_built_in_event_sources(skill_text):
    section = _section(skill_text, "Built-in Event Sources")
    for source in BUILT_IN_SOURCES:
        assert f"`{source}`" in section


def test_github_is_not_the_only_built_in_source(skill_text, readme_text):
    assert "**GitHub** is a built-in integration" not in skill_text
    assert "For services other than GitHub" not in skill_text
    assert "Register webhooks for any service" not in readme_text


def test_sources_come_from_the_deployment_capabilities(skill_text):
    section = _section(skill_text, "Built-in Event Sources")
    assert "/api/automation/v1/capabilities" in section
    assert "`eventSources`" in section
    assert "Never invent a source name" in section


def test_trigger_source_field_points_at_the_capabilities(skill_text):
    row = next(
        line for line in skill_text.splitlines() if line.startswith("| `trigger.source`")
    )
    assert "`eventSources`" in row


def test_setup_form_comes_before_the_api(skill_text):
    section = _section(skill_text, "Agent Canvas Setup Form")
    assert "`automation_form_update`" in section
    assert "Do not create, update, enable" in section
    # The rule must come before the creation steps that deploy through the API.
    assert skill_text.index("## Agent Canvas Setup Form") < skill_text.index(
        "## Automation Creation Process"
    )
    steps = _section(skill_text, "Automation Creation Process")
    assert "`automation_form_update`" in steps.splitlines()[1]


def test_readme_describes_the_setup_form_and_sources(readme_text):
    assert "`automation_form_update`" in readme_text
    for source in BUILT_IN_SOURCES:
        assert f"`{source}`" in readme_text


def test_creation_guidance_requires_selected_agent_profile(skill_text):
    creation = _section(skill_text, "Automation Creation Process")
    assert "agent_profile_id" in creation
    for heading in ("Prompt Preset", "Plugin Preset", "Plugin Spec Automations"):
        assert '"agent_profile_id"' in _section(skill_text, heading)
    assert "does not accept `model`, `agent_profile_name`, or `agent_profile_id`" not in skill_text
