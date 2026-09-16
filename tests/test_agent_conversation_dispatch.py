import json
from unittest.mock import MagicMock
from uuid import UUID

import github_client


def _dispatcher(monkeypatch):
    monkeypatch.setenv("AGENT_SERVER_URL", "http://agent")
    monkeypatch.setenv("SESSION_API_KEY", "session")
    monkeypatch.setenv(
        "AUTOMATION_AGENT_PROFILE_ID", "11111111-1111-4111-8111-111111111111"
    )
    monkeypatch.setenv(
        "AUTOMATION_EVENT_PAYLOAD", json.dumps({"automation_id": "automation-1"})
    )
    return github_client.AgentConversationDispatcher()


def test_new_subject_uses_selected_profile_and_persists_mapping(monkeypatch):
    state = {}
    monkeypatch.setattr(
        github_client,
        "_kv_request",
        lambda method, value=None: state.update(value or {}) if method == "PUT" else state,
    )
    monkeypatch.setattr("openhands.tools.register_default_tools", lambda: None)
    workspace = MagicMock()
    workspace.__enter__.return_value = workspace
    monkeypatch.setattr(github_client, "RemoteWorkspace", lambda **kwargs: workspace)
    missing = RuntimeError("missing")
    missing.response = MagicMock(status_code=404)
    monkeypatch.setattr(
        github_client.RemoteConversation, "attach", MagicMock(side_effect=missing)
    )
    conversation = MagicMock()
    create = MagicMock(return_value=conversation)
    monkeypatch.setattr(github_client.RemoteConversation, "create", create)

    result = _dispatcher(monkeypatch).deliver("repo:issue:7", "revision-1", "work")

    request = create.call_args.args[1]
    assert request.agent_profile_id == UUID(
        "11111111-1111-4111-8111-111111111111"
    )
    assert request.initial_message.run is True
    assert result["disposition"] == "created"
    assert state["repo:issue:7"]["conversation_id"] == result["conversation_id"]


def test_known_subject_resumes_once_per_delivery(monkeypatch):
    state = {
        "repo:pr:9": {
            "conversation_id": "22222222-2222-4222-8222-222222222222",
            "delivery": "head-1",
        }
    }
    monkeypatch.setattr(
        github_client,
        "_kv_request",
        lambda method, value=None: state.update(value or {}) if method == "PUT" else state,
    )
    monkeypatch.setattr("openhands.tools.register_default_tools", lambda: None)
    workspace = MagicMock()
    workspace.__enter__.return_value = workspace
    monkeypatch.setattr(github_client, "RemoteWorkspace", lambda **kwargs: workspace)
    conversation = MagicMock()
    attach = MagicMock(return_value=conversation)
    monkeypatch.setattr(github_client.RemoteConversation, "attach", attach)
    dispatcher = _dispatcher(monkeypatch)

    duplicate = dispatcher.deliver("repo:pr:9", "head-1", "old")
    resumed = dispatcher.deliver("repo:pr:9", "head-2", "new")

    assert duplicate["disposition"] == "deduplicated"
    assert resumed["disposition"] == "resumed"
    conversation.send_message.assert_called_once_with("new")
    conversation.run.assert_called_once_with(blocking=False)
