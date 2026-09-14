"""Verify shared support is included in independently installed skills."""

import subprocess
import sys
from pathlib import Path

import pytest
from openhands.sdk.skills import install_skill

ROOT = Path(__file__).resolve().parents[1]


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
