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
        # A caller with no revision identity records an empty head, which keeps
        # the dedupe keyed on `delivery` alone.
        "head": "",
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
    conversation.update_secrets.assert_called_once_with(dispatcher._secrets)
    if should_run:
        conversation.run.assert_called_once_with(blocking=False)
    else:
        conversation.run.assert_not_called()


def test_new_delivery_on_a_running_same_head_is_not_a_second_review(monkeypatch):
    """A fresh trigger for a head already under review must not start a review.

    This is the duplicate the trigger-keyed delivery alone allowed: a second
    review request (or a label re-applied after the bot's own handoff) produces a
    new delivery key, which would send a new turn and publish a second review of
    the head an in-flight conversation is already reviewing.
    """
    state = {
        _state_key("repo:pr:9"): {
            "subject": "repo:pr:9",
            "conversation_id": "22222222-2222-4222-8222-222222222222",
            "delivery": "42:head-2",
            "head": "head-2",
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
    conversation.state.execution_status = ConversationExecutionStatus.RUNNING
    monkeypatch.setattr(
        agent_conversation.RemoteConversation,
        "attach",
        MagicMock(return_value=conversation),
    )

    with _dispatcher(monkeypatch) as dispatcher:
        result = dispatcher.deliver("repo:pr:9", "43:head-2", "again", head="head-2")

    assert result["disposition"] == "in_progress"
    conversation.send_message.assert_not_called()
    conversation.run.assert_not_called()
    # The revision the live turn is working on is left recorded, not overwritten
    # by the trigger that arrived beside it.
    assert state[_state_key("repo:pr:9")]["delivery"] == "42:head-2"


def test_new_delivery_on_a_running_new_head_still_sends_a_turn(monkeypatch):
    """A moved head is new work, so the running conversation gets the new turn."""
    state = {
        _state_key("repo:pr:9"): {
            "subject": "repo:pr:9",
            "conversation_id": "22222222-2222-4222-8222-222222222222",
            "delivery": "42:head-1",
            "head": "head-1",
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
    conversation.state.execution_status = ConversationExecutionStatus.RUNNING
    monkeypatch.setattr(
        agent_conversation.RemoteConversation,
        "attach",
        MagicMock(return_value=conversation),
    )

    with _dispatcher(monkeypatch) as dispatcher:
        result = dispatcher.deliver("repo:pr:9", "43:head-2", "next", head="head-2")

    assert result["disposition"] == "resumed"
    conversation.send_message.assert_called_once_with("next")
    conversation.run.assert_called_once_with(blocking=False)
    assert state[_state_key("repo:pr:9")] == {
        "subject": "repo:pr:9",
        "conversation_id": result["conversation_id"],
        "delivery": "43:head-2",
        "head": "head-2",
    }


def _errored_local_conversation(monkeypatch):
    monkeypatch.setattr(agent_conversation, "_register_tools", lambda: None)
    workspace = MagicMock()
    workspace.__enter__.return_value = workspace
    workspace.get_secrets.return_value = {}
    monkeypatch.setattr(
        agent_conversation, "RemoteWorkspace", lambda **kwargs: workspace
    )
    conversation = MagicMock()
    conversation.state.execution_status = ConversationExecutionStatus.ERROR
    monkeypatch.setattr(
        agent_conversation.RemoteConversation,
        "attach",
        MagicMock(return_value=conversation),
    )
    return conversation


def test_errored_conversation_retries_its_delivery(monkeypatch):
    """A matched delivery whose conversation died is retried, not deduplicated.

    The delivery string never changes for a stable subject, so treating ERROR as
    "deduplicated" would strand that subject forever with its work unfinished.
    """
    state = {
        _state_key("repo:pr:9"): {
            "subject": "repo:pr:9",
            "conversation_id": "22222222-2222-4222-8222-222222222222",
            "delivery": "head-1",
        }
    }
    _fake_kv(monkeypatch, state)
    conversation = _errored_local_conversation(monkeypatch)

    with _dispatcher(monkeypatch) as dispatcher:
        result = dispatcher.deliver("repo:pr:9", "head-1", "old")

    assert result["disposition"] == "retried"
    conversation.update_secrets.assert_called_once_with(dispatcher._secrets)
    conversation.send_message.assert_called_once_with("old")
    conversation.run.assert_called_once_with(blocking=False)
    assert state[_state_key("repo:pr:9")]["error_retries"] == 1


def test_errored_conversation_stops_retrying_after_the_bound(monkeypatch):
    """A conversation that keeps failing is not re-run on every scan."""
    state = {
        _state_key("repo:pr:9"): {
            "subject": "repo:pr:9",
            "conversation_id": "22222222-2222-4222-8222-222222222222",
            "delivery": "head-1",
            "error_retries": agent_conversation._MAX_ERROR_RETRIES,
        }
    }
    _fake_kv(monkeypatch, state)
    conversation = _errored_local_conversation(monkeypatch)

    with _dispatcher(monkeypatch) as dispatcher:
        result = dispatcher.deliver("repo:pr:9", "head-1", "old")

    assert result["disposition"] == "deduplicated"
    conversation.send_message.assert_not_called()
    conversation.run.assert_not_called()


def test_new_delivery_resets_the_error_retry_count(monkeypatch):
    state = {
        _state_key("repo:pr:9"): {
            "subject": "repo:pr:9",
            "conversation_id": "22222222-2222-4222-8222-222222222222",
            "delivery": "head-1",
            "error_retries": agent_conversation._MAX_ERROR_RETRIES,
        }
    }
    _fake_kv(monkeypatch, state)
    conversation = _errored_local_conversation(monkeypatch)

    with _dispatcher(monkeypatch) as dispatcher:
        result = dispatcher.deliver("repo:pr:9", "head-2", "new")

    assert result["disposition"] == "resumed"
    conversation.send_message.assert_called_once_with("new")
    assert "error_retries" not in state[_state_key("repo:pr:9")]


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


# --- OpenHands Cloud and Enterprise: conversations go through the OpenHands API


class _FakeCloud:
    """The OpenHands API's conversations, as the dispatcher uses them."""

    def __init__(self, conversation=None):
        self.conversation = conversation
        self.started = []
        self.sent = []

    def get(self, conversation_id):
        return self.conversation

    def start(self, conversation_id, profile_id, title, prompt):
        self.started.append({"id": str(conversation_id), "profile": str(profile_id)})

    def send(self, conversation, prompt):
        self.sent.append(prompt)

    def run(self, conversation):
        pass


def _cloud_dispatcher(monkeypatch, cloud):
    monkeypatch.delenv("AGENT_SERVER_URL", raising=False)
    monkeypatch.setenv("SESSION_API_KEY", "session")
    monkeypatch.setenv(
        "AUTOMATION_AGENT_PROFILE_ID", "11111111-1111-4111-8111-111111111111"
    )
    monkeypatch.setenv(
        "AUTOMATION_EVENT_PAYLOAD", json.dumps({"automation_id": "automation-1"})
    )
    monkeypatch.setattr(agent_conversation, "CloudConversations", lambda: cloud)
    return agent_conversation.AgentConversationDispatcher()


def test_cloud_run_starts_a_new_subject_with_the_selected_profile(monkeypatch):
    # Arrange
    state = {}
    _fake_kv(monkeypatch, state)
    cloud = _FakeCloud()

    # Act
    with _cloud_dispatcher(monkeypatch, cloud) as dispatcher:
        result = dispatcher.deliver("repo:pr:7", "revision-1", "review it")

    # Assert
    assert result["disposition"] == "created"
    [started] = cloud.started
    assert started["profile"] == "11111111-1111-4111-8111-111111111111"
    assert state[_state_key("repo:pr:7")]["conversation_id"] == started["id"]


def test_cloud_run_does_not_start_a_second_conversation_while_one_is_starting(
    monkeypatch,
):
    # Arrange - the first delivery's conversation is not listed by the API yet
    state = {}
    _fake_kv(monkeypatch, state)
    cloud = _FakeCloud()
    with _cloud_dispatcher(monkeypatch, cloud) as dispatcher:
        dispatcher.deliver("repo:pr:7", "revision-1", "review it", head="sha-1")
        recorded = dict(state[_state_key("repo:pr:7")])

        # Act - a new revision arrives before it is
        result = dispatcher.deliver(
            "repo:pr:7", "revision-2", "review again", head="sha-2"
        )

    # Assert - nothing is started, and the record is left for the next trigger
    assert result["disposition"] == "in_progress"
    assert len(cloud.started) == 1
    assert state[_state_key("repo:pr:7")] == recorded


def test_cloud_run_sends_a_new_revision_to_the_subjects_conversation(monkeypatch):
    # Arrange
    state = {
        _state_key("repo:pr:7"): {
            "conversation_id": "22222222-2222-4222-8222-222222222222",
            "delivery": "revision-1",
            "head": "sha-1",
        }
    }
    _fake_kv(monkeypatch, state)
    cloud = _FakeCloud({"sandbox_status": "RUNNING", "execution_status": "idle"})

    # Act
    with _cloud_dispatcher(monkeypatch, cloud) as dispatcher:
        result = dispatcher.deliver(
            "repo:pr:7", "revision-2", "review again", head="sha-2"
        )

    # Assert
    assert result["disposition"] == "resumed"
    assert cloud.sent == ["review again"]
    assert cloud.started == []


def test_cloud_run_replaces_a_conversation_whose_sandbox_is_gone(monkeypatch):
    # Arrange
    gone = "22222222-2222-4222-8222-222222222222"
    state = {
        _state_key("repo:pr:7"): {
            "conversation_id": gone,
            "delivery": "revision-1",
            "head": "sha-1",
        }
    }
    _fake_kv(monkeypatch, state)
    cloud = _FakeCloud({"sandbox_status": "MISSING", "execution_status": None})

    # Act
    with _cloud_dispatcher(monkeypatch, cloud) as dispatcher:
        result = dispatcher.deliver(
            "repo:pr:7", "revision-2", "review again", head="sha-2"
        )

    # Assert - the API does not start an id twice, so the subject gets a new one
    assert result["disposition"] == "created"
    [started] = cloud.started
    assert started["id"] != gone
    assert state[_state_key("repo:pr:7")]["conversation_id"] == started["id"]


def test_cloud_run_retries_a_delivery_whose_conversation_errored(monkeypatch):
    # Arrange
    state = {
        _state_key("repo:pr:7"): {
            "conversation_id": "22222222-2222-4222-8222-222222222222",
            "delivery": "revision-1",
            "head": "sha-1",
        }
    }
    _fake_kv(monkeypatch, state)
    cloud = _FakeCloud({"sandbox_status": "RUNNING", "execution_status": "error"})

    # Act
    with _cloud_dispatcher(monkeypatch, cloud) as dispatcher:
        result = dispatcher.deliver("repo:pr:7", "revision-1", "review it", head="sha-1")

    # Assert
    assert result["disposition"] == "retried"
    assert cloud.sent == ["review it"]
    assert cloud.started == []
    assert state[_state_key("repo:pr:7")]["error_retries"] == 1


def test_cloud_run_stops_retrying_an_errored_delivery_after_the_bound(monkeypatch):
    # Arrange
    state = {
        _state_key("repo:pr:7"): {
            "conversation_id": "22222222-2222-4222-8222-222222222222",
            "delivery": "revision-1",
            "head": "sha-1",
            "error_retries": agent_conversation._MAX_ERROR_RETRIES,
        }
    }
    _fake_kv(monkeypatch, state)
    cloud = _FakeCloud({"sandbox_status": "RUNNING", "execution_status": "error"})

    # Act
    with _cloud_dispatcher(monkeypatch, cloud) as dispatcher:
        result = dispatcher.deliver("repo:pr:7", "revision-1", "review it", head="sha-1")

    # Assert
    assert result["disposition"] == "deduplicated"
    assert cloud.sent == []
