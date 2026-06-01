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
        if stripped in {"run: |", "script: |"}:
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
