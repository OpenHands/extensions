import json
from unittest.mock import MagicMock
from uuid import NAMESPACE_URL, UUID, uuid5

import agent_conversation
import github_client
import pytest
from openhands.sdk.conversation.state import ConversationExecutionStatus
from openhands.sdk.secret import LookupSecret


def _dispatcher(monkeypatch):
    monkeypatch.setenv("AGENT_SERVER_URL", "http://agent")
    monkeypatch.setenv("SESSION_API_KEY", "session")
    monkeypatch.setenv(
        "AUTOMATION_AGENT_PROFILE_ID", "11111111-1111-4111-8111-111111111111"
    )
    monkeypatch.setenv(
        "AUTOMATION_EVENT_PAYLOAD", json.dumps({"automation_id": "automation-1"})
    )
    return agent_conversation.AgentConversationDispatcher()


def _state_key(subject):
    conversation_id = uuid5(NAMESPACE_URL, f"automation-1:{subject}")
    return f"agent-conversation-{conversation_id}"


def _fake_kv(monkeypatch, state):
    def request(key, method, value=None):
        if method == "GET":
            return state.get(key)
        state[key] = value
        return {"key": key, "value": value}

    monkeypatch.setattr(agent_conversation, "_kv_request", request)


def test_github_secret_falls_back_to_agent_server(monkeypatch):
    monkeypatch.delenv("REVIEW_TOKEN", raising=False)
    monkeypatch.setenv("AGENT_SERVER_URL", "http://agent")
    monkeypatch.setenv("SESSION_API_KEY", "session")
    secret = MagicMock()
    secret.get_value.return_value = "saved-token"
    workspace = MagicMock()
    workspace.get_secrets.return_value = {"REVIEW_TOKEN": secret}
    monkeypatch.setattr(
        "openhands.sdk.workspace.RemoteWorkspace", lambda **kwargs: workspace
    )

    assert github_client._load_secret("REVIEW_TOKEN") == "saved-token"
    workspace.get_secrets.assert_called_once_with(["REVIEW_TOKEN"])
    workspace.reset_client.assert_called_once_with()


def test_new_subject_uses_selected_profile_and_persists_mapping(monkeypatch):
    state = {}
    _fake_kv(monkeypatch, state)
    monkeypatch.setattr(agent_conversation, "_register_tools", lambda: None)
    workspace = MagicMock()
    workspace.__enter__.return_value = workspace
    scoped_secrets = {
        "GITHUB_TOKEN": LookupSecret(url="/api/settings/secrets/GITHUB_TOKEN")
    }
    workspace.get_secrets.return_value = scoped_secrets
    monkeypatch.setattr(
        agent_conversation, "RemoteWorkspace", lambda **kwargs: workspace
    )
    missing = agent_conversation.httpx.HTTPStatusError(
        "missing",
        request=MagicMock(),
        response=MagicMock(status_code=404),
    )
    monkeypatch.setattr(
        agent_conversation.RemoteConversation, "attach", MagicMock(side_effect=missing)
    )
    conversation = MagicMock()
    create = MagicMock(return_value=conversation)
    monkeypatch.setattr(agent_conversation.RemoteConversation, "create", create)

    with _dispatcher(monkeypatch) as dispatcher:
        result = dispatcher.deliver("repo:issue:7", "revision-1", "work")

    request = create.call_args.args[1]
    assert request.agent_profile_id == UUID("11111111-1111-4111-8111-111111111111")
    assert request.secrets == scoped_secrets
    workspace.get_secrets.assert_called_once_with(
        agent_profile_id="11111111-1111-4111-8111-111111111111"
    )
    assert request.initial_message.run is True
    assert result["disposition"] == "created"
    record = state[_state_key("repo:issue:7")]
    assert record == {
        "subject": "repo:issue:7",
        "conversation_id": result["conversation_id"],
        "delivery": "revision-1",
    }


def test_known_subject_resumes_once_per_delivery(monkeypatch):
    state = {
        _state_key("repo:pr:9"): {
            "subject": "repo:pr:9",
            "conversation_id": "22222222-2222-4222-8222-222222222222",
            "delivery": "head-1",
        }
    }
    _fake_kv(monkeypatch, state)
    monkeypatch.setattr(agent_conversation, "_register_tools", lambda: None)
    workspace = MagicMock()
    workspace.__enter__.return_value = workspace
    scoped_secrets = {
        "GITHUB_TOKEN": LookupSecret(url="/api/settings/secrets/GITHUB_TOKEN")
    }
    workspace.get_secrets.return_value = scoped_secrets
    monkeypatch.setattr(
        agent_conversation, "RemoteWorkspace", lambda **kwargs: workspace
    )
    conversation = MagicMock()
    conversation.state.execution_status = ConversationExecutionStatus.FINISHED
    attach = MagicMock(return_value=conversation)
    monkeypatch.setattr(agent_conversation.RemoteConversation, "attach", attach)
    with _dispatcher(monkeypatch) as dispatcher:
        duplicate = dispatcher.deliver("repo:pr:9", "head-1", "old")
        resumed = dispatcher.deliver("repo:pr:9", "head-2", "new")

    assert duplicate["disposition"] == "deduplicated"
    assert resumed["disposition"] == "resumed"
    conversation.update_secrets.assert_called_once_with(scoped_secrets)
    conversation.send_message.assert_called_once_with("new")
    conversation.run.assert_called_once_with(blocking=False)


@pytest.mark.parametrize(
    ("status", "disposition", "should_run"),
    [
        (ConversationExecutionStatus.IDLE, "resumed", True),
        (ConversationExecutionStatus.PAUSED, "resumed", True),
        (ConversationExecutionStatus.RUNNING, "in_progress", False),
    ],
)
def test_same_delivery_resumes_only_inactive_conversation(
    monkeypatch, status, disposition, should_run
):
    state = {
        _state_key("repo:pr:9"): {
            "subject": "repo:pr:9",
            "conversation_id": "22222222-2222-4222-8222-222222222222",
            "delivery": "head-1",
        }
    }
    _fake_kv(monkeypatch, state)
    monkeypatch.setattr(agent_conversation, "_register_tools", lambda: None)
    workspace = MagicMock()
    workspace.__enter__.return_value = workspace
    workspace.get_secrets.return_value = {}
    monkeypatch.setattr(
        agent_conversation, "RemoteWorkspace", lambda **kwargs: workspace
    )
    conversation = MagicMock()
    conversation.state.execution_status = status
    monkeypatch.setattr(
        agent_conversation.RemoteConversation,
        "attach",
        MagicMock(return_value=conversation),
    )

    with _dispatcher(monkeypatch) as dispatcher:
        result = dispatcher.deliver("repo:pr:9", "head-1", "old")

    assert result["disposition"] == disposition
    conversation.send_message.assert_not_called()
    if should_run:
        conversation.run.assert_called_once_with(blocking=False)
    else:
        conversation.update_secrets.assert_not_called()
        conversation.run.assert_not_called()


def test_subjects_use_independent_kv_records(monkeypatch):
    state = {}
    _fake_kv(monkeypatch, state)
    monkeypatch.setattr(agent_conversation, "_register_tools", lambda: None)
    workspace = MagicMock()
    workspace.__enter__.return_value = workspace
    workspace.get_secrets.return_value = {}
    monkeypatch.setattr(
        agent_conversation, "RemoteWorkspace", lambda **kwargs: workspace
    )
    missing = agent_conversation.httpx.HTTPStatusError(
        "missing",
        request=MagicMock(),
        response=MagicMock(status_code=404),
    )
    monkeypatch.setattr(
        agent_conversation.RemoteConversation, "attach", MagicMock(side_effect=missing)
    )
    monkeypatch.setattr(
        agent_conversation.RemoteConversation,
        "create",
        MagicMock(side_effect=[MagicMock(), MagicMock()]),
    )

    with _dispatcher(monkeypatch) as dispatcher:
        dispatcher.deliver("repo:issue:7", "revision-1", "first")
        dispatcher.deliver("repo:issue:8", "revision-1", "second")

    assert set(state) == {
        _state_key("repo:issue:7"),
        _state_key("repo:issue:8"),
    }
