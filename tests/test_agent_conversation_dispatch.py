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
    """An in-memory Automation KV store with the conditional-write semantics.

    The store versions its whole state document, so a write carries the version
    it read and loses with a 409-equivalent (here, `KVConflictError`) when
    another writer got there first. The real store holds one row lock across the
    read-modify-write, so the check and the set here are serialized under a lock;
    that is what makes the version check meaningful between threads. `state` is
    the plain key->value mapping the tests assert against.
    """
    import threading

    versions = {"value": 0}
    lock = threading.Lock()

    def request(key, method, value=None, *, query=None):
        query = query or {}
        with lock:
            if method == "GET":
                if key not in state:
                    return None
                if query.get("meta") in (True, "true"):
                    return {
                        "key": key,
                        "value": state[key],
                        "version": versions["value"],
                    }
                return {"key": key, "value": state[key]}
            if query.get("nx") in (True, "true") and key in state:
                raise agent_conversation.KVConflictError(key)
            if "if_version" in query:
                expected = query["if_version"]
                expected = (
                    int(expected) if not isinstance(expected, int) else expected
                )
                if expected != versions["value"]:
                    raise agent_conversation.KVConflictError(key)
            state[key] = value
            versions["value"] += 1
            return {"key": key, "value": value}

    monkeypatch.setattr(agent_conversation, "_kv_request", request)
    return state


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


def _tracked_dispatcher(monkeypatch, state, statuses, max_in_flight=None):
    """The shipped dispatcher with tracking on and the agent server stubbed.

    `statuses` maps conversation_id -> execution_status; an id absent from it is
    answered as a 404, which is how a conversation the server no longer has looks.
    `max_in_flight` is the cap the dispatcher admits against; None means track
    without capping, matching the pre-existing tests.
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
    return agent_conversation.AgentConversationDispatcher(
        track_in_flight=True, max_in_flight=max_in_flight
    )


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
        # Age the reservation past the pending grace so a 404 is believed: a
        # just-reserved slot is held while its conversation is being created.
        registry = state[agent_conversation._IN_FLIGHT_KEY]
        for entry in registry.values():
            entry["started_at"] = (
                agent_conversation.time.time()
                - agent_conversation._PENDING_GRACE_SECONDS
                - 1
            )
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
        state[agent_conversation._IN_FLIGHT_KEY] = {
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
        state[agent_conversation._IN_FLIGHT_KEY] = {
            "unknown": {"subject": "repo:pr:1"}
        }
        active._execution_status = lambda cid: "running"
        assert active.in_flight() == 1


def test_a_conversation_the_server_no_longer_has_releases_its_slot(monkeypatch):
    """A 404 past the reservation grace counts as gone, freeing the slot once."""
    state = {}
    dispatcher = _tracked_dispatcher(monkeypatch, state, {})
    with dispatcher as active:
        active.deliver("repo:pr:9", "head-1", "work")
        registry = state[agent_conversation._IN_FLIGHT_KEY]
        for entry in registry.values():
            entry["started_at"] = (
                agent_conversation.time.time()
                - agent_conversation._PENDING_GRACE_SECONDS
                - 1
            )
        assert active.in_flight() == 0
    assert state[agent_conversation._IN_FLIGHT_KEY] == {}


def test_a_just_reserved_slot_is_held_until_its_conversation_exists(monkeypatch):
    """A 404 within the reservation grace is "not created yet", not "gone".

    A slot is reserved just before its conversation is created. A concurrent
    admission that reads the registry in that window must keep counting the
    reservation, or it would free a slot that is about to be used and start a
    runtime past the cap.
    """
    state = {}
    dispatcher = _tracked_dispatcher(monkeypatch, state, {}, max_in_flight=1)
    with dispatcher as active:
        first = active.deliver("repo:pr:9", "head-1", "work")
        assert first["disposition"] == "created"
        # The conversation does not exist yet, so the server answers 404.
        second = active.deliver("repo:pr:10", "head-10", "work")
    assert second["disposition"] == "deferred"
    assert agent_conversation.RemoteConversation.create.call_count == 1


def test_release_drops_a_conversation_from_the_registry(monkeypatch):
    state = {
        agent_conversation._IN_FLIGHT_KEY: {
            "one": {
                "subject": "repo:pr:1",
                "started_at": agent_conversation.time.time(),
            }
        }
    }
    dispatcher = _tracked_dispatcher(monkeypatch, state, {})
    with dispatcher as active:
        active.release("one")
        assert state[agent_conversation._IN_FLIGHT_KEY] == {}


# --------------------------------------------------------------------------- #
# Atomic admission: the in-flight cap is enforced by the dispatcher itself, at
# launch time, through a conditional read-modify-write of the registry. A scan's
# earlier read is only a pre-filter; this is what cannot be raced, and it is the
# one gate both the scheduled and the event launch paths pass through.
# --------------------------------------------------------------------------- #


def _counting_dispatcher(monkeypatch, state, statuses, max_in_flight):
    return _tracked_dispatcher(
        monkeypatch, state, statuses, max_in_flight=max_in_flight
    )


def test_admission_refuses_a_new_conversation_at_the_cap(monkeypatch):
    """A third conversation under a cap of two is refused, not started."""
    live = {"conv-1": {"subject": "a"}, "conv-2": {"subject": "b"}}
    state = {agent_conversation._IN_FLIGHT_KEY: dict(live)}
    dispatcher = _counting_dispatcher(
        monkeypatch, state, {"/api/conversations/conv-1": "running",
                             "/api/conversations/conv-2": "running"}, 2
    )
    created = agent_conversation.RemoteConversation.create
    with dispatcher as active:
        result = active.deliver("repo:pr:3", "head-3", "work")
    assert result["disposition"] == "deferred"
    created.assert_not_called()
    # The refused conversation left no delivery record, so the request retries.
    assert state[agent_conversation._IN_FLIGHT_KEY] == live


def test_admission_starts_under_the_cap_and_reserves_the_slot(monkeypatch):
    state = {
        agent_conversation._IN_FLIGHT_KEY: {
            "conv-1": {"subject": "a", "started_at": agent_conversation.time.time()}
        }
    }
    dispatcher = _counting_dispatcher(
        monkeypatch, state, {"/api/conversations/conv-1": "running"}, 2
    )
    with dispatcher as active:
        result = active.deliver("repo:pr:3", "head-3", "work")
    assert result["disposition"] == "created"
    registry = state[agent_conversation._IN_FLIGHT_KEY]
    assert set(registry) == {"conv-1", result["conversation_id"]}


def test_admission_refuses_at_a_zero_cap(monkeypatch):
    """A cap of zero refuses even the first conversation, atomically."""
    state = {}
    dispatcher = _counting_dispatcher(monkeypatch, state, {}, 0)
    with dispatcher as active:
        result = active.deliver("repo:pr:3", "head-3", "work")
    assert result["disposition"] == "deferred"
    assert state.get(agent_conversation._IN_FLIGHT_KEY) is None


def test_admission_creates_the_registry_atomically_for_the_first_conversation(
    monkeypatch,
):
    state = {}
    dispatcher = _counting_dispatcher(monkeypatch, state, {}, 4)
    with dispatcher as active:
        result = active.deliver("repo:pr:3", "head-3", "work")
    assert result["disposition"] == "created"
    assert list(state[agent_conversation._IN_FLIGHT_KEY]) == [
        result["conversation_id"]
    ]


def test_admission_retries_a_lost_race_instead_of_overshooting(monkeypatch):
    """A conditional write that loses a race re-reads and cannot over-admit.

    The fake store rejects the first conditional write as though a concurrent
    run had written first, and adds a live conversation behind the dispatcher's
    back. The retry must observe that conversation and refuse, rather than trust
    its own earlier read and start beyond the cap.
    """
    state = {
        agent_conversation._IN_FLIGHT_KEY: {
            "conv-1": {"subject": "a", "started_at": agent_conversation.time.time()}
        }
    }
    dispatcher = _counting_dispatcher(
        monkeypatch, state, {"/api/conversations/conv-1": "running"}, 2
    )
    original = agent_conversation._kv_request
    failed = {"once": False}

    def racy(key, method, value=None, *, query=None):
        query = query or {}
        if (
            method == "PUT"
            and key == agent_conversation._IN_FLIGHT_KEY
            and "if_version" in query
            and not failed["once"]
        ):
            failed["once"] = True
            # A concurrent run claimed the other slot.
            original(
                key,
                "PUT",
                {
                    "conv-1": {"subject": "a", "started_at": 0},
                    "conv-2": {"subject": "b", "started_at": 0},
                },
            )
            raise agent_conversation.KVConflictError(key)
        return original(key, method, value, query=query)

    monkeypatch.setattr(agent_conversation, "_kv_request", racy)
    with dispatcher as active:
        active._execution_status = lambda cid: "running"
        result = active.deliver("repo:pr:3", "head-3", "work")
    assert result["disposition"] == "deferred"
    assert agent_conversation.RemoteConversation.create.call_count == 0


def test_admission_is_additive_across_concurrent_bursts(monkeypatch):
    """Ten concurrent deliveries under a cap of two reserve exactly two slots.

    This is the burst the event path can produce: simultaneous deliveries racing
    the same read-modify-write. Only the outer cap may be admitted no matter the
    interleaving.
    """
    import threading

    state = {}
    dispatcher = _counting_dispatcher(monkeypatch, state, {}, 2)
    created = agent_conversation.RemoteConversation.create
    results = []
    lock = threading.Lock()

    def run(subject):
        # Each delivery needs its own admission attempt against the one store.
        with dispatcher as active:
            active._execution_status = lambda cid: "running"
            result = active.deliver(subject, f"head-{subject}", "work")
        with lock:
            results.append(result["disposition"])

    threads = [threading.Thread(target=run, args=(f"pr-{i}",)) for i in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results.count("created") == 2
    assert results.count("deferred") == 8
    assert created.call_count == 2
    assert len(state[agent_conversation._IN_FLIGHT_KEY]) == 2


def test_a_failed_creation_releases_the_reserved_slot(monkeypatch):
    """A runtime that fails to come up must not hold a slot until it ages out."""
    state = {}
    dispatcher = _counting_dispatcher(monkeypatch, state, {}, 1)
    agent_conversation.RemoteConversation.create.side_effect = RuntimeError("boom")
    with dispatcher as active:
        with pytest.raises(RuntimeError, match="boom"):
            active.deliver("repo:pr:3", "head-3", "work")
    # The reservation was rolled back, so the slot is free again.
    assert state.get(agent_conversation._IN_FLIGHT_KEY) == {}


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
