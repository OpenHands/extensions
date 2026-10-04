"""Tests for how the stale-CI pull request closer reports its run."""

import json

import pytest
from github_automation_helpers import worker


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        pytest.param(
            {"AUTOMATION_CALLBACK_API_KEY": "callback-key"},
            "Bearer callback-key",
            id="local-run-uses-its-callback-key",
        ),
        pytest.param(
            {"OPENHANDS_API_KEY": "openhands-key"},
            "Bearer openhands-key",
            id="cloud-run-has-no-callback-key-and-uses-its-api-key",
        ),
    ],
)
def test_completion_is_reported_with_the_key_the_run_was_given(
    tmp_path, monkeypatch, environment, expected
):
    # Arrange
    module = worker("github-stale-ci-pr-closer", tmp_path, monkeypatch)
    for name in ("AUTOMATION_CALLBACK_API_KEY", "OPENHANDS_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("AUTOMATION_CALLBACK_URL", "https://automation.test/callback")
    monkeypatch.setenv("AUTOMATION_RUN_ID", "run-1")
    sent = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def urlopen(request):
        sent.append(request)
        return _Response()

    monkeypatch.setattr(module, "urlopen", urlopen)

    # Act
    module.complete_run()

    # Assert
    [request] = sent
    assert request.get_header("Authorization") == expected
    assert json.loads(request.data) == {"status": "COMPLETED", "run_id": "run-1"}
