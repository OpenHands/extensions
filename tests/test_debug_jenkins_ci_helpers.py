import importlib.util
import logging
import sys
from datetime import datetime
from pathlib import Path

import pytest

SCRIPTS_DIR = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "debug-jenkins-ci"
    / "scripts"
)
AGENT_SCRIPT_PATH = SCRIPTS_DIR / "agent_script.py"
PROMPT_PATH = SCRIPTS_DIR / "prompt.py"


def load_module(name: str, path: Path):
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


jenkins_agent_script = load_module(
    "debug_jenkins_ci_agent_script",
    AGENT_SCRIPT_PATH,
)
jenkins_prompt = load_module("debug_jenkins_ci_prompt", PROMPT_PATH)


def make_logs(total_lines: int, error_line: int | None = None) -> str:
    lines = []
    for i in range(1, total_lines + 1):
        prefix = f"line {i:02d} "
        if i == error_line:
            lines.append(prefix + "ERROR: boom " + "x" * 48)
        else:
            lines.append(prefix + "x" * 60)
    return "\n".join(lines)


def test_jenkins_find_error_context_extracts_around_first_match():
    logs = make_logs(total_lines=20, error_line=10)

    result = jenkins_agent_script._find_error_context(
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


def test_jenkins_find_error_context_skips_invalid_patterns(caplog):
    logs = make_logs(total_lines=12, error_line=6)

    with caplog.at_level(logging.WARNING):
        result = jenkins_agent_script._find_error_context(
            logs,
            max_size=300,
            error_patterns=[r"(", r"ERROR"],
        )

    assert result is not None
    assert "line 06 ERROR: boom" in result
    assert "Skipping invalid error pattern" in caplog.text


def test_jenkins_truncate_logs_falls_back_to_head_tail_when_no_error_context():
    logs = "abcdefghijklmnopqrstuvwxyz" * 4

    result = jenkins_agent_script._truncate_logs(logs, max_size=30)

    assert result.startswith(logs[:12])
    assert result.endswith(logs[-18:])
    assert "[... 74 characters truncated ...]" in result


def test_format_duration_handles_seconds_minutes_and_hours():
    assert jenkins_agent_script.format_duration(45_000) == "45s"
    assert jenkins_agent_script.format_duration(61_000) == "1m 1s"
    assert jenkins_agent_script.format_duration(3_661_000) == "1h 1m 1s"


def test_format_timestamp_uses_local_datetime_format():
    timestamp_ms = 1_700_000_000_000
    expected = datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")

    assert jenkins_agent_script.format_timestamp(timestamp_ms) == expected


def test_format_prompt_renders_valid_inputs():
    prompt = jenkins_prompt.format_prompt(
        jenkins_url="https://jenkins.example.com",
        job_name="folder/my-job",
        build_number="123",
        build_result="FAILURE",
        duration="1m 1s",
        timestamp="2025-01-01 12:00:00",
        stages="❌ **Test**: FAILED (12.0s)",
        logs="Traceback: boom",
    )

    assert "https://jenkins.example.com" in prompt
    assert "folder/my-job" in prompt
    assert "123" in prompt
    assert "Traceback: boom" in prompt


def test_format_prompt_rejects_invalid_inputs():
    with pytest.raises(jenkins_prompt.PromptValidationError):
        jenkins_prompt.format_prompt(
            jenkins_url="not-a-url",
            job_name="folder/my-job",
            build_number="123",
            build_result="FAILURE",
            duration="1m 1s",
            timestamp="2025-01-01 12:00:00",
            stages="none",
            logs="logs",
        )

    with pytest.raises(jenkins_prompt.PromptValidationError):
        jenkins_prompt.format_prompt(
            jenkins_url="https://jenkins.example.com",
            job_name="folder/my job",
            build_number="123",
            build_result="FAILURE",
            duration="1m 1s",
            timestamp="2025-01-01 12:00:00",
            stages="none",
            logs="logs",
        )

    with pytest.raises(jenkins_prompt.PromptValidationError):
        jenkins_prompt.format_prompt(
            jenkins_url="https://jenkins.example.com",
            job_name="folder/my-job",
            build_number="12a",
            build_result="FAILURE",
            duration="1m 1s",
            timestamp="2025-01-01 12:00:00",
            stages="none",
            logs="logs",
        )
