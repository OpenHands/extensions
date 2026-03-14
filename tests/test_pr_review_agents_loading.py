import importlib.util
import os
import sys
from pathlib import Path


def _load_agent_script_module():
    os.environ["OPENHANDS_SUPPRESS_BANNER"] = "1"
    script_path = (
        Path(__file__).parent.parent
        / "plugins"
        / "pr-review"
        / "scripts"
        / "agent_script.py"
    )
    spec = importlib.util.spec_from_file_location("pr_review_agent_script", script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["pr_review_agent_script"] = module
    spec.loader.exec_module(module)
    return module


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_load_review_skills_merges_nested_agents_for_changed_paths(
    monkeypatch, tmp_path
):
    module = _load_agent_script_module()

    _write_file(tmp_path / ".git", "gitdir: .git")
    _write_file(tmp_path / "AGENTS.md", "root policy\n")
    _write_file(tmp_path / "packages" / "AGENTS.md", "package policy\n")
    _write_file(tmp_path / "packages" / "sdk" / "AGENTS.md", "sdk policy\n")
    _write_file(tmp_path / "packages" / "other" / "AGENTS.md", "other policy\n")
    _write_file(tmp_path / ".agents" / "skills" / "reviewer.md", "review guidance\n")

    monkeypatch.setattr(
        module,
        "get_pr_changed_files",
        lambda pr_number: ["packages/sdk/api.py"],
    )

    skills = module.load_review_skills(tmp_path, "106")

    assert [skill.name for skill in skills] == ["agents", "reviewer"]

    agents_skill = skills[0]
    assert "root policy" in agents_skill.content
    assert "package policy" in agents_skill.content
    assert "sdk policy" in agents_skill.content
    assert "other policy" not in agents_skill.content
    assert agents_skill.content.index("root policy") < agents_skill.content.index(
        "package policy"
    )
    assert agents_skill.content.index("package policy") < agents_skill.content.index(
        "sdk policy"
    )
    assert "## AGENTS.md" in agents_skill.content
    assert "## packages/AGENTS.md" in agents_skill.content
    assert "## packages/sdk/AGENTS.md" in agents_skill.content

    reviewer_skill = skills[1]
    assert reviewer_skill.content == "review guidance"


def test_load_review_skills_adds_package_agents_without_repo_root_agents(
    monkeypatch, tmp_path
):
    module = _load_agent_script_module()

    _write_file(tmp_path / ".git", "gitdir: .git")
    _write_file(tmp_path / "packages" / "sdk" / "AGENTS.md", "sdk policy\n")

    monkeypatch.setattr(
        module,
        "get_pr_changed_files",
        lambda pr_number: ["packages/sdk/api.py"],
    )

    skills = module.load_review_skills(tmp_path, "106")

    assert [skill.name for skill in skills] == ["agents"]
    assert skills[0].content == "sdk policy\n"
