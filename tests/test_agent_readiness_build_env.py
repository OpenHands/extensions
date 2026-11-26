"""Exercise the public build-environment scanner on real repository fixtures."""

import subprocess
from pathlib import Path

import pytest


SCANNER = (
    Path(__file__).resolve().parents[1]
    / "plugins/onboarding/skills/agent-readiness-report/scripts/scan_build_env.sh"
)


def scan(repo: Path) -> str:
    result = subprocess.run(
        ["bash", str(SCANNER), str(repo)], capture_output=True, text=True
    )
    # The diagnostic scanner's existing final conditional may return nonzero.
    # Its output, not that incidental status, is the contract under test.
    assert result.stderr == ""
    return result.stdout


def section(output: str, title: str) -> str:
    return output.split(f"-- {title} --\n", 1)[1].split("\n-- ", 1)[0]


@pytest.mark.parametrize("name", ["Justfile", "justfile", ".justfile", "JuStFiLe"])
def test_root_justfile_is_listed_once_and_scanned(tmp_path, name):
    (tmp_path / name).write_text("# Build with just build\nbuild:\n\techo built\n")
    output = scan(tmp_path)
    assert section(output, "Setup scripts").splitlines().count(f"./{name}") == 1
    assert f"1 build command references in {name}" in section(output, "Build commands")


@pytest.mark.parametrize("name", ["README.md", "AGENTS.md"])
def test_documented_just_build_command_is_counted(tmp_path, name):
    (tmp_path / name).write_text("Build with `just build`.\n")
    assert f"1 build command references in {name}" in scan(tmp_path)


def test_makefile_only_keeps_existing_detection(tmp_path):
    (tmp_path / "Makefile").write_text("# Run make build\nbuild:\n\techo built\n")
    output = scan(tmp_path)
    assert section(output, "Setup scripts").strip() == "./Makefile"
    assert section(output, "Build commands").strip() == (
        "1 build command references in Makefile"
    )


def test_repository_without_build_files_has_no_false_justfile_entries(tmp_path):
    output = scan(tmp_path)
    assert section(output, "Setup scripts").strip() == ""
    assert section(output, "Build commands").strip() == ""
