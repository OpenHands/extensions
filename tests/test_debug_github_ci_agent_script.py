import importlib.util
import logging
import sys
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "debug-github-ci"
    / "scripts"
    / "agent_script.py"
)
MODULE_NAME = "debug_github_ci_agent_script"


def load_agent_script_module():
    sys.modules.pop(MODULE_NAME, None)
    spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


agent_script = load_agent_script_module()


def make_logs(total_lines: int, error_line: int | None = None) -> str:
    lines = []
    for i in range(1, total_lines + 1):
        prefix = f"line {i:02d} "
        if i == error_line:
            lines.append(prefix + "ERROR: boom " + "x" * 48)
        else:
            lines.append(prefix + "x" * 60)
    return "\n".join(lines)


def test_find_error_context_extracts_around_first_match():
    logs = make_logs(total_lines=20, error_line=10)

    result = agent_script._find_error_context(
        logs,
        max_size=350,
        error_patterns=[r"ERROR"],
    )

    assert result is not None
    assert "[Context extracted around error at line 10. Original log: 20 lines]" in result
    assert "line 09" in result
    assert "line 10 ERROR: boom" in result
    assert "line 13" in result
    assert "line 08" not in result


def test_find_error_context_skips_invalid_patterns(caplog):
    logs = make_logs(total_lines=12, error_line=6)

    with caplog.at_level(logging.WARNING):
        result = agent_script._find_error_context(
            logs,
            max_size=300,
            error_patterns=[r"(", r"ERROR"],
        )

    assert result is not None
    assert "line 06 ERROR: boom" in result
    assert "Skipping invalid error pattern" in caplog.text


def test_truncate_logs_falls_back_to_head_tail_when_no_error_context():
    logs = "abcdefghijklmnopqrstuvwxyz" * 4

    result = agent_script._truncate_logs(logs, max_size=30)

    assert result.startswith(logs[:12])
    assert result.endswith(logs[-18:])
    assert "[... 74 characters truncated ...]" in result


def test_format_failed_jobs_lists_only_failed_jobs_and_steps():
    jobs = [
        {
            "name": "lint",
            "conclusion": "success",
            "steps": [{"name": "ruff", "conclusion": "success"}],
        },
        {
            "name": "tests",
            "conclusion": "failure",
            "steps": [
                {"name": "setup", "conclusion": "success"},
                {"name": "pytest", "conclusion": "failure"},
                {"name": "upload", "conclusion": "failure"},
            ],
        },
        {
            "name": "docs",
            "conclusion": "failure",
            "steps": [],
        },
    ]

    result = agent_script.format_failed_jobs(jobs)

    assert "lint" not in result
    assert "### Job: tests" in result
    assert "  - pytest" in result
    assert "  - upload" in result
    assert "### Job: docs" in result


def test_format_failed_jobs_handles_no_failures():
    jobs = [{"name": "lint", "conclusion": "success", "steps": []}]

    assert agent_script.format_failed_jobs(jobs) == "No failed jobs found."
