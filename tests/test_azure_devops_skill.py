"""The azure-devops skill describes plain git, not token-in-URL workarounds."""

from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).parent.parent / "skills" / "azure-devops"


@pytest.fixture(params=["SKILL.md", "README.md"])
def skill_text(request):
    return (SKILL_DIR / request.param).read_text()


def test_git_uses_plain_commands_and_clone_url(skill_text):
    assert "Use plain `git clone`" in skill_text
    assert (
        "GIT_TERMINAL_PROMPT=0 git clone https://dev.azure.com/ORG/PROJECT/_git/REPO"
        in skill_text
    )


def test_no_token_in_remote_url(skill_text):
    assert "git remote set-url" not in skill_text
    assert "${AZURE_DEVOPS_TOKEN}@" not in skill_text
    assert "$AZURE_DEVOPS_TOKEN@" not in skill_text


def test_no_credential_helper_token_file(skill_text):
    assert "azure-devops-access-token" not in skill_text


def test_token_is_not_described_as_pat_only(skill_text):
    assert "Microsoft Entra" in skill_text
    assert "with your Personal Access Token (PAT)" not in skill_text


def test_basic_auth_header_is_a_single_line(skill_text):
    # GNU base64 wraps at 76 columns, which splits long Entra tokens.
    assert "base64 | tr -d '\\n'" in skill_text
