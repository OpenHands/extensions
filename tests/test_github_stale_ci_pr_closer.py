"""Tests for how the stale-CI pull request closer keeps state and reports its run."""

import io
import json
from urllib.error import HTTPError

import pytest
from github_automation_helpers import worker

RECORDS = {"7": {"head_sha": "abc", "first_failed_at": 0}}


@pytest.fixture
def kv(tmp_path, monkeypatch):
    """A KV store that, like the real one, keeps a PUT body verbatim."""
    module = worker("github-stale-ci-pr-closer", tmp_path, monkeypatch)
    monkeypatch.setattr(module, "KV_TOKEN", "kv-token")
    monkeypatch.setattr(module, "KV_BASE", "https://automation.test")
    store = {}

    def urlopen(request):
        if request.get_method() == "PUT":
            store["value"] = json.loads(request.data)
        elif "value" not in store:
            raise HTTPError(request.full_url, 404, "Not Found", {}, None)
        return io.BytesIO(json.dumps({"value": store["value"]}).encode())

    monkeypatch.setattr(module, "urlopen", urlopen)
    return module, store


def test_state_round_trips_through_the_kv_store_unchanged(kv):
    # Arrange
    module, store = kv
    state = {"prs": RECORDS}

    # Act
    for _ in range(3):
        module.save_state("OpenHands/extensions", state)
        state = module.load_state("OpenHands/extensions")

    # Assert
    assert store["value"] == {"version": 1, "prs": RECORDS}
    assert state == store["value"]


def test_state_nested_by_earlier_versions_is_recovered(kv):
    # Arrange
    module, store = kv
    oldest = {"value": {"version": 1, "prs": {}}}
    store["value"] = {"value": {"value": oldest, "version": 1, "prs": RECORDS}}

    # Act
    state = module.load_state("OpenHands/extensions")

    # Assert
    assert state == {"version": 1, "prs": RECORDS}


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
