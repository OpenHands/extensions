import json
from types import SimpleNamespace

import pytest


def test_create_conversation_builds_payload(monkeypatch):
    from skills.openhands_api.scripts.openhands_api import OpenHandsAPI

    captured = {}

    class FakeResp:
        def __init__(self, payload):
            self._payload = payload
            self.ok = True
            self.status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"conversation_id": "abc", "status": "ok"}

    class FakeSession:
        def __init__(self):
            self.headers = {}

        def post(self, url, json=None):
            captured["url"] = url
            captured["json"] = json
            return FakeResp(json)

        def get(self, url, params=None):
            raise AssertionError("unexpected")

        def __getattr__(self, name):
            if name == "headers":
                return self.headers
            raise AttributeError(name)

    # Patch requests.Session to our fake
    import skills.openhands_api.scripts.openhands_api as mod

    monkeypatch.setattr(mod.requests, "Session", lambda: FakeSession())

    api = OpenHandsAPI(api_key="k", base_url="https://example.com/")
    api.create_conversation(
        initial_user_msg="hi",
        repository="o/r",
        selected_branch="main",
        git_provider="github",
    )

    assert captured["url"] == "https://example.com/api/conversations"
    assert captured["json"] == {
        "initial_user_msg": "hi",
        "repository": "o/r",
        "selected_branch": "main",
        "git_provider": "github",
    }


def test_get_events_clamps_limit_and_params(monkeypatch):
    from skills.openhands_api.scripts.openhands_api import OpenHandsAPI

    captured = {}

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"events": [], "has_more": False}

    class FakeSession:
        def __init__(self):
            self.headers = {}

        def get(self, url, params=None):
            captured["url"] = url
            captured["params"] = params
            return FakeResp()

        def post(self, url, json=None):
            raise AssertionError("unexpected")

    import skills.openhands_api.scripts.openhands_api as mod

    monkeypatch.setattr(mod.requests, "Session", lambda: FakeSession())

    api = OpenHandsAPI(api_key="k", base_url="https://example.com")
    api.get_events("cid", limit=1000, reverse=True, start_id=5, end_id=6)

    assert captured["url"] == "https://example.com/api/conversations/cid/events"
    assert captured["params"]["limit"] == 100
    assert captured["params"]["reverse"] == "true"
    assert captured["params"]["start_id"] == 5
    assert captured["params"]["end_id"] == 6
