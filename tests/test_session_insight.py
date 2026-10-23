import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/session-insight/scripts/generate_insight_report.py"


def run_report(tmp_path: Path, *inputs: Path) -> subprocess.CompletedProcess[str]:
    output = tmp_path / "usage" / "report.html"
    command = [sys.executable, str(SCRIPT), "--output", str(output)]
    for item in inputs:
        command.extend(("--input", str(item)))
    return subprocess.run(command, capture_output=True, text=True, check=False)


def test_generates_self_contained_evidence_report(tmp_path):
    session = tmp_path / "session.json"
    session.write_text(
        json.dumps(
            {
                "events": [
                    {"tool_name": "execute_bash", "status": "success"},
                    {
                        "tool_name": "execute_bash",
                        "status": "failed",
                        "error": "timeout",
                    },
                    {"tool_name": "execute_bash", "status": "success"},
                    {
                        "tool_name": "file_editor",
                        "status": "failed",
                        "error_detail": {"kind": "invalid"},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    result = run_report(tmp_path, session)

    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["records"] == 4
    report = (tmp_path / "usage" / "report.html").read_text(encoding="utf-8")
    assert report.startswith("<!doctype html>")
    assert "execute_bash" in report
    assert "timeout" in report
    assert str(session.resolve()) in report


def test_excludes_credential_like_files_and_values(tmp_path):
    safe = tmp_path / "sessions" / "events.jsonl"
    safe.parent.mkdir()
    event = (
        '{"command":"curl -H Authorization:must-not-render",'
        '"status":"success","api_key":"must-not-render"}\n'
    )
    safe.write_text(event * 3, encoding="utf-8")
    secret = tmp_path / "sessions" / "auth-token.json"
    secret.write_text('{"token":"also-must-not-render"}', encoding="utf-8")
    for name in (
        "credentials.json",
        "secrets.json",
        "tokens.json",
        "cookies.json",
        "api_keys.json",
    ):
        (tmp_path / "sessions" / name).write_text(
            '{"tool_name":"must-not-count"}', encoding="utf-8"
        )

    result = run_report(tmp_path, safe.parent)

    assert result.returncode == 0
    report = (tmp_path / "usage" / "report.html").read_text(encoding="utf-8")
    assert "must-not-render" not in report
    assert "auth-token.json" not in report
    assert "command" in report


def test_reads_real_sdk_action_and_observation_events_once(tmp_path):
    session = tmp_path / "conversation"
    session.mkdir()
    (session / "action.json").write_text(
        json.dumps(
            {
                "kind": "ActionEvent",
                "tool_name": "execute_bash",
                "action": {"command": "false"},
            }
        ),
        encoding="utf-8",
    )
    (session / "observation.json").write_text(
        json.dumps(
            {
                "kind": "ObservationEvent",
                "tool_name": "execute_bash",
                "observation": {
                    "is_error": True,
                    "exit_code": 1,
                    "content": "command failed",
                },
            }
        ),
        encoding="utf-8",
    )

    result = run_report(tmp_path, session)

    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["failure_signals"] == 1
    report = (tmp_path / "usage" / "report.html").read_text(encoding="utf-8")
    assert "tool error" in report
    assert "execute_bash" not in report  # One call is below the repetitive threshold.


def test_no_records_exits_without_creating_report(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()

    result = run_report(tmp_path, empty)

    assert result.returncode == 2
    assert "No supported OpenHands session records were found" in result.stderr
    assert not (tmp_path / "usage" / "report.html").exists()


def test_malformed_file_is_reported_but_valid_data_still_runs(tmp_path):
    source = tmp_path / "sessions"
    source.mkdir()
    (source / "broken.json").write_text("{", encoding="utf-8")
    (source / "valid.json").write_text(
        '[{"action":"edit","status":"success"}]', encoding="utf-8"
    )

    result = run_report(tmp_path, source)

    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["malformed_files"] == 1


def test_counts_conversation_error_event_by_classification(tmp_path):
    session = tmp_path / "conversation.jsonl"
    session.write_text(
        json.dumps(
            {
                "source": "environment",
                "code": "LLMAuthenticationError",
                "detail": "invalid api key",
                "classification": {
                    "kind": "auth",
                    "retryable": False,
                    "user_action": "settings",
                },
                "kind": "ConversationErrorEvent",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_report(tmp_path, session)

    assert result.returncode == 0
    assert json.loads(result.stdout)["failure_signals"] == 1
    report = (tmp_path / "usage" / "report.html").read_text(encoding="utf-8")
    assert "auth" in report
    assert "invalid api key" not in report
