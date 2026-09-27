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
    conversation.update_secrets.assert_called_once_with(dispatcher._secrets)
    if should_run:
        conversation.run.assert_called_once_with(blocking=False)
    else:
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


# --------------------------------------------------------------------------- #
# In-flight registry: a dispatcher asked to track its work records every
# conversation it starts and counts the nonterminal ones on demand, so a
# scheduled scan can bound live runtimes across runs.
# --------------------------------------------------------------------------- #


def _tracked_dispatcher(monkeypatch, state, statuses):
    """The shipped dispatcher with tracking on and the agent server stubbed.

    `statuses` maps conversation_id -> execution_status; an id absent from it is
    answered as a 404, which is how a conversation the server no longer has looks.
    """
    monkeypatch.setenv("AGENT_SERVER_URL", "http://agent")
    monkeypatch.setenv("SESSION_API_KEY", "session")
    monkeypatch.setenv(
        "AUTOMATION_AGENT_PROFILE_ID", "11111111-1111-4111-8111-111111111111"
    )
    monkeypatch.setenv(
        "AUTOMATION_EVENT_PAYLOAD", json.dumps({"automation_id": "automation-1"})
    )
    _fake_kv(monkeypatch, state)
    monkeypatch.setattr(agent_conversation, "_register_tools", lambda: None)
    workspace = MagicMock()
    workspace.__enter__.return_value = workspace
    workspace.get_secrets.return_value = {}
    monkeypatch.setattr(
        agent_conversation, "RemoteWorkspace", lambda **kwargs: workspace
    )
    missing = agent_conversation.httpx.HTTPStatusError(
        "missing", request=MagicMock(), response=MagicMock(status_code=404)
    )
    monkeypatch.setattr(
        agent_conversation.RemoteConversation, "attach", MagicMock(side_effect=missing)
    )
    monkeypatch.setattr(
        agent_conversation.RemoteConversation,
        "create",
        MagicMock(side_effect=lambda *a, **k: MagicMock()),
    )

    def get(path):
        response = MagicMock()
        if path in statuses:
            response.status_code = 200
            response.json.return_value = {"execution_status": statuses[path]}
        else:
            response.status_code = 404
        return response

    workspace.client.get = get
    return agent_conversation.AgentConversationDispatcher(track_in_flight=True)


def test_a_started_conversation_is_recorded_and_counted_while_live(monkeypatch):
    state = {}
    conversation_id = None
    dispatcher = _tracked_dispatcher(monkeypatch, state, {})
    with dispatcher as active:
        result = active.deliver("repo:pr:9", "head-1", "work")
        conversation_id = result["conversation_id"]
        active._execution_status = lambda cid: "running"
        assert active.in_flight() == 1

    registry = state[agent_conversation._IN_FLIGHT_KEY]
    assert list(registry) == [conversation_id]
    assert registry[conversation_id]["subject"] == "repo:pr:9"


def test_in_flight_is_none_when_tracking_is_off(monkeypatch):
    """A dispatcher not asked to track must report no signal, not zero."""
    state = {}
    monkeypatch.setenv("AGENT_SERVER_URL", "http://agent")
    monkeypatch.setenv("SESSION_API_KEY", "session")
    monkeypatch.setenv(
        "AUTOMATION_AGENT_PROFILE_ID", "11111111-1111-4111-8111-111111111111"
    )
    monkeypatch.setenv(
        "AUTOMATION_EVENT_PAYLOAD", json.dumps({"automation_id": "automation-1"})
    )
    _fake_kv(monkeypatch, state)
    monkeypatch.setattr(agent_conversation, "_register_tools", lambda: None)
    workspace = MagicMock()
    workspace.__enter__.return_value = workspace
    workspace.get_secrets.return_value = {}
    monkeypatch.setattr(
        agent_conversation, "RemoteWorkspace", lambda **kwargs: workspace
    )
    dispatcher = agent_conversation.AgentConversationDispatcher()
    with dispatcher as active:
        assert active.in_flight() is None
    assert state == {}


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("running", 1),
        ("waiting_for_confirmation", 1),
        ("idle", 1),
        ("paused", 1),
        ("finished", 0),
        ("error", 0),
        ("stuck", 0),
        (None, 0),
    ],
)
def test_only_nonterminal_conversations_hold_capacity(monkeypatch, status, expected):
    """Completed, errored, and missing conversations all release their slot."""
    state = {}
    dispatcher = _tracked_dispatcher(monkeypatch, state, {})
    with dispatcher as active:
        active.deliver("repo:pr:9", "head-1", "work")
        active._execution_status = lambda cid: status
        assert active.in_flight() == expected


def test_an_abandoned_registry_entry_releases_its_slot_without_a_status_read(
    monkeypatch,
):
    """An entry older than the abandonment window is not asked about at all."""
    state = {}
    dispatcher = _tracked_dispatcher(monkeypatch, state, {})
    reads = []
    stale = (
        agent_conversation.time.time()
        - agent_conversation._ABANDONED_AFTER_SECONDS
        - 1
    )
    with dispatcher as active:
        active._registry = lambda: {
            "old-conversation": {"subject": "repo:pr:1", "started_at": stale},
            "live-conversation": {
                "subject": "repo:pr:2",
                "started_at": agent_conversation.time.time(),
            },
        }

        def status(cid):
            reads.append(cid)
            return "running"

        active._execution_status = status
        assert active.in_flight() == 1

    assert reads == ["live-conversation"]


def test_an_entry_with_no_timestamp_counts_as_live(monkeypatch):
    """An unknown age is treated as live, not as abandoned, so the slot is held."""
    state = {}
    dispatcher = _tracked_dispatcher(monkeypatch, state, {})
    with dispatcher as active:
        active._registry = lambda: {"unknown": {"subject": "repo:pr:1"}}
        active._execution_status = lambda cid: "running"
        assert active.in_flight() == 1


def test_a_conversation_the_server_no_longer_has_releases_its_slot(monkeypatch):
    """A 404 from the agent server counts as gone, freeing the slot once."""
    state = {}
    dispatcher = _tracked_dispatcher(monkeypatch, state, {})
    with dispatcher as active:
        active.deliver("repo:pr:9", "head-1", "work")
        assert active.in_flight() == 0
    assert state[agent_conversation._IN_FLIGHT_KEY] == {}


def test_release_drops_a_conversation_from_the_registry(monkeypatch):
    state = {}
    dispatcher = _tracked_dispatcher(monkeypatch, state, {})
    with dispatcher as active:
        active._registry = lambda: {
            "one": {"subject": "repo:pr:1", "started_at": agent_conversation.time.time()}
        }
        active.release("one")
        assert state[agent_conversation._IN_FLIGHT_KEY] == {}
