import importlib.util
import sys
from pathlib import Path


def _load_openhands_api_module():
    skill_path = Path(__file__).parent.parent / "skills" / "openhands-api" / "scripts" / "openhands_api.py"
    spec = importlib.util.spec_from_file_location("openhands_api", skill_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["openhands_api"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_app_conversation_start_builds_v1_payload(monkeypatch):
    mod = _load_openhands_api_module()
    OpenHandsAPI = mod.OpenHandsAPI

    captured = {}

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "task-1", "status": "WORKING"}

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def post(self, url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            captured["timeout"] = timeout
            return FakeResp()

        def close(self):
            return None

    monkeypatch.setattr(mod.httpx, "Client", lambda **kwargs: FakeClient(**kwargs))

    api = OpenHandsAPI(api_key="k", base_url="https://example.com/")
    resp = api.app_conversation_start(
        initial_message="hi",
        selected_repository="o/r",
        selected_branch="main",
        title="Test title",
        run=False,
    )

    assert resp == {"id": "task-1", "status": "WORKING"}
    assert captured["url"] == "https://example.com/api/v1/app-conversations"
    assert captured["timeout"] == 120
    assert captured["json"] == {
        "initial_message": {
            "role": "user",
            "content": [{"type": "text", "text": "hi"}],
            "run": False,
        },
        "selected_repository": "o/r",
        "selected_branch": "main",
        "title": "Test title",
    }


def test_app_conversations_get_batch_passes_ids(monkeypatch):
    mod = _load_openhands_api_module()
    OpenHandsAPI = mod.OpenHandsAPI

    captured = {}

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return [{"id": "conv-1"}]

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get(self, url, params=None):
            captured["url"] = url
            captured["params"] = params
            return FakeResp()

        def close(self):
            return None

    monkeypatch.setattr(mod.httpx, "Client", lambda **kwargs: FakeClient(**kwargs))

    api = OpenHandsAPI(api_key="k", base_url="https://example.com")
    conversations = api.app_conversations_get_batch(ids=["conv-1", "conv-2"])

    assert conversations == [{"id": "conv-1"}]
    assert captured["url"] == "https://example.com/api/v1/app-conversations"
    assert captured["params"] == {"ids": ["conv-1", "conv-2"]}


def test_poll_start_task_until_ready_uses_start_task_endpoint(monkeypatch):
    mod = _load_openhands_api_module()
    OpenHandsAPI = mod.OpenHandsAPI

    states = [
        {"id": "task-1", "status": "WORKING"},
        {"id": "task-1", "status": "READY", "app_conversation_id": "conv-1"},
    ]
    call_count = {"sleep": 0}

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get(self, url, params=None):
            class FakeResp:
                def raise_for_status(self_nonlocal):
                    return None

                def json(self_nonlocal):
                    return [states.pop(0)]

            return FakeResp()

        def close(self):
            return None

    monkeypatch.setattr(mod.httpx, "Client", lambda **kwargs: FakeClient(**kwargs))
    monkeypatch.setattr(mod.time, "sleep", lambda *_args, **_kwargs: call_count.__setitem__("sleep", call_count["sleep"] + 1))

    api = OpenHandsAPI(api_key="k", base_url="https://example.com")
    ready = api.poll_start_task_until_ready("task-1", timeout_s=10, poll_interval_s=0.01, backoff_factor=1.0)

    assert ready == {"id": "task-1", "status": "READY", "app_conversation_id": "conv-1"}
    assert call_count["sleep"] == 1


def test_legacy_alias_still_exists(monkeypatch):
    mod = _load_openhands_api_module()

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def close(self):
            return None

    monkeypatch.setattr(mod.httpx, "Client", lambda **kwargs: FakeClient(**kwargs))

    api = mod.OpenHandsV1API(api_key="k")
    assert isinstance(api, mod.OpenHandsAPI)
