import importlib.util
import io
import urllib.error
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "issue-duplicate-checker" / "scripts"


def load_script(name: str):
    path = PLUGIN_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_action_shell_blocks_do_not_interpolate_expressions_directly():
    action_path = ROOT / "plugins" / "issue-duplicate-checker" / "action.yml"
    lines = action_path.read_text().splitlines()
    in_block = False
    block_indent = 0
    for line_number, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if in_block and stripped and indent <= block_indent:
            in_block = False
        if stripped.startswith(("run:", "script:")):
            block_scalar = stripped.split(":", 1)[1].strip()
            if block_scalar.startswith(("|", ">")):
                in_block = True
                block_indent = indent
            continue
        assert not (in_block and "${{" in line), (
            f"Move GitHub expression on line {line_number} into env before using it"
        )


def test_normalize_result_preserves_model_should_comment_false():
    script = load_script("issue_duplicate_check_openhands")

    result = script.normalize_result(
        {
            "should_comment": False,
            "is_duplicate": True,
            "auto_close_candidate": True,
            "classification": "duplicate",
            "confidence": "high",
            "canonical_issue_number": 123,
            "candidate_issues": [{"number": 123}],
        }
    )

    assert result["should_comment"] is False
    assert result["auto_close_candidate"] is False


def test_github_headers_require_token(monkeypatch):
    script = load_script("issue_duplicate_check_openhands")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(
        RuntimeError,
        match="GITHUB_TOKEN environment variable is required",
    ):
        script.github_headers()

    monkeypatch.setenv("GITHUB_TOKEN", "token")
    headers = script.github_headers()
    assert headers["Authorization"] == "Bearer token"


def test_issue_check_request_json_raises_structured_http_error(monkeypatch):
    script = load_script("issue_duplicate_check_openhands")

    def fake_urlopen(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="https://api.example.test/example",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=io.BytesIO(b'{"message":"rate limited"}'),
        )

    monkeypatch.setattr(script.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(script.HTTPError) as exc_info:
        script.request_json("https://api.example.test", "/example")

    assert exc_info.value.status_code == 403
    assert exc_info.value.url == "https://api.example.test/example"


def test_parse_agent_json_extracts_fenced_json():
    script = load_script("issue_duplicate_check_openhands")

    result = script.parse_agent_json(
        'Here is the result:\n```json\n'
        '{"classification":"duplicate","confidence":"high"}\n```'
    )

    assert result == {"classification": "duplicate", "confidence": "high"}


def test_normalize_result_guards_auto_close_and_infers_canonical_issue():
    script = load_script("issue_duplicate_check_openhands")

    overlapping = script.normalize_result(
        {
            "should_comment": True,
            "is_duplicate": False,
            "auto_close_candidate": True,
            "classification": "overlapping-scope",
            "confidence": "high",
            "candidate_issues": [{"number": 10}],
        }
    )
    assert overlapping["should_comment"] is True
    assert overlapping["auto_close_candidate"] is False

    low_confidence = script.normalize_result(
        {
            "should_comment": True,
            "is_duplicate": True,
            "auto_close_candidate": True,
            "classification": "duplicate",
            "confidence": "low",
            "candidate_issues": [{"number": 11}],
        }
    )
    assert low_confidence["should_comment"] is False
    assert low_confidence["auto_close_candidate"] is False

    inferred = script.normalize_result(
        {
            "should_comment": True,
            "is_duplicate": True,
            "auto_close_candidate": True,
            "classification": "duplicate",
            "confidence": "high",
            "canonical_issue_number": None,
            "candidate_issues": [{"number": "12"}],
        }
    )
    assert inferred["auto_close_candidate"] is True
    assert inferred["canonical_issue_number"] == 12


def test_build_prompt_includes_required_schema_keys():
    script = load_script("issue_duplicate_check_openhands")

    prompt = script.build_prompt(
        "OpenHands/extensions",
        {
            "number": 123,
            "title": "Duplicate bug",
            "body": "Looks related",
            "html_url": "https://github.com/OpenHands/extensions/issues/123",
        },
    )

    for key in [
        "should_comment",
        "is_duplicate",
        "auto_close_candidate",
        "classification",
        "confidence",
        "canonical_issue_number",
        "candidate_issues",
    ]:
        assert key in prompt


def test_find_latest_auto_close_comment_uses_newest_auto_close_marker():
    script = load_script("auto_close_duplicate_issues")

    latest, canonical = script.find_latest_auto_close_comment(
        [
            {
                "id": 1,
                "created_at": "2026-01-01T00:00:00Z",
                "body": "<!-- openhands-duplicate-check canonical=10 auto-close=true -->",
            },
            {
                "id": 2,
                "created_at": "2026-01-03T00:00:00Z",
                "body": "<!-- openhands-duplicate-check canonical=20 auto-close=false -->",
            },
            {
                "id": 3,
                "created_at": None,
                "body": "<!-- openhands-duplicate-check canonical=30 auto-close=true -->",
            },
            {
                "id": 4,
                "created_at": "2026-01-02T00:00:00Z",
                "body": "<!-- openhands-duplicate-check canonical=40 auto-close=true -->",
            },
        ]
    )

    assert latest["id"] == 4
    assert canonical == 40


def test_request_json_raises_structured_http_error(monkeypatch):
    script = load_script("auto_close_duplicate_issues")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    def fake_urlopen(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="https://api.github.com/example",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=io.BytesIO(b'{"message":"missing"}'),
        )

    monkeypatch.setattr(script.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(script.HTTPError) as exc_info:
        script.request_json("/example")

    assert exc_info.value.status_code == 404
    assert exc_info.value.path == "/example"


def test_fetch_issue_returns_none_on_404(monkeypatch):
    script = load_script("auto_close_duplicate_issues")

    def fake_request_json(path):
        raise script.HTTPError("GET", path, 404, "missing")

    monkeypatch.setattr(script, "request_json", fake_request_json)

    assert script.fetch_issue("OpenHands/extensions", 123) is None
