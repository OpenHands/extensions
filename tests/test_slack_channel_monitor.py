import os
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).parent.parent
    / "skills"
    / "slack-channel-monitor"
    / "scripts"
    / "main.py"
)


def load_slack_monitor_helpers():
    os.environ["WORKSPACE_BASE"] = "/tmp/openhands/workspaces/slack-monitor-test/run"
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    helper_source = source.split("\nPOLL_ITERATIONS = 10", 1)[0]
    namespace: dict = {}
    exec(compile(helper_source, str(SCRIPT_PATH), "exec"), namespace)
    return namespace


def test_post_message_sends_markdown_text(monkeypatch):
    helpers = load_slack_monitor_helpers()
    posted: dict = {}

    def fake_slack_post(token: str, endpoint: str, body: dict) -> dict:
        posted["token"] = token
        posted["endpoint"] = endpoint
        posted["body"] = body
        return {"ts": "123.456"}

    monkeypatch.setitem(helpers, "slack_post", fake_slack_post)
    markdown_summary = "- **Bold:** [link](https://example.com)"

    ts = helpers["post_message"](
        "xoxb-test",
        "C123",
        markdown_summary,
        thread_ts="111.222",
    )

    assert ts == "123.456"
    assert posted["endpoint"] == "chat.postMessage"
    assert posted["body"] == {
        "channel": "C123",
        "markdown_text": markdown_summary,
        "unfurl_links": False,
        "unfurl_media": False,
        "thread_ts": "111.222",
    }
    assert "text" not in posted["body"]
    assert "blocks" not in posted["body"]
    assert "mrkdwn" not in posted["body"]


def test_completed_response_includes_llm_provenance(monkeypatch):
    helpers = load_slack_monitor_helpers()
    monkeypatch.setattr(helpers["time"], "time", lambda: 100.0)
    monkeypatch.setitem(helpers, "conversation_status", lambda *_: "finished")
    monkeypatch.setitem(
        helpers,
        "conversation_final_response",
        lambda *_: ("evt-1", "Completed the request."),
    )
    posted: list[str] = []
    monkeypatch.setitem(
        helpers,
        "post_message",
        lambda _token, _channel, text, thread_ts=None: posted.append(text) or "2.0",
    )
    rec = {
        "conversation_id": "conv-1",
        "channel_id": "C123",
        "thread_ts": "1.0",
        "last_activity": 0.0,
        "llm_profile": "slack-profile",
        "llm_model": "anthropic/claude-sonnet-4-6",
    }

    helpers["_check_conversation_completion"](
        "C123:1.0", rec, "http://agent", "key", "xoxb-test", []
    )

    assert posted == [
        "Completed the request.\n\n"
        "LLM profile: `slack-profile` · Model: `anthropic/claude-sonnet-4-6`"
    ]


def test_followup_quiet_poll_is_capped_at_watch_expiry(monkeypatch):
    helpers = load_slack_monitor_helpers()
    monkeypatch.setattr(helpers["time"], "time", lambda: 950.0)
    calls: list[tuple[str, str, str]] = []

    def fake_thread_replies(
        token: str,
        channel: str,
        thread_ts: str,
        oldest: str,
    ) -> list[dict]:
        calls.append((channel, thread_ts, oldest))
        return []

    monkeypatch.setitem(helpers, "thread_replies", fake_thread_replies)
    rec = {
        "channel_id": "C123",
        "thread_ts": "900.000000",
        "status": "watching",
        "last_seen_reply_ts": "900.000000",
        "reply_poll_backoff_seconds": 80,
        "next_reply_poll_at": 950.0,
        "watch_until": 1000.0,
    }

    replies = helpers["_poll_due_thread_replies"](
        "xoxb-test",
        {"C123:900.000000": rec},
        "UBOT",
        [],
    )

    assert replies == []
    assert calls == [("C123", "900.000000", "900.000000")]
    assert rec["status"] == "watching"
    assert rec["next_reply_poll_at"] == 1000.0


def test_expired_followup_watch_polls_once_before_closing(monkeypatch):
    helpers = load_slack_monitor_helpers()
    monkeypatch.setattr(helpers["time"], "time", lambda: 1001.0)
    trigger = helpers["TRIGGER_PHRASE"]
    reply = {
        "ts": "999.500000",
        "user": "U1",
        "text": f"{trigger} please continue",
    }
    calls: list[tuple[str, str, str]] = []

    def fake_thread_replies(
        token: str,
        channel: str,
        thread_ts: str,
        oldest: str,
    ) -> list[dict]:
        calls.append((channel, thread_ts, oldest))
        return [reply]

    monkeypatch.setitem(helpers, "thread_replies", fake_thread_replies)
    rec = {
        "channel_id": "C123",
        "thread_ts": "900.000000",
        "status": "watching",
        "last_seen_reply_ts": "900.000000",
        "reply_poll_backoff_seconds": 160,
        "next_reply_poll_at": 1100.0,
        "watch_until": 1000.0,
    }

    replies = helpers["_poll_due_thread_replies"](
        "xoxb-test",
        {"C123:900.000000": rec},
        "UBOT",
        [],
    )

    assert calls == [("C123", "900.000000", "900.000000")]
    assert replies == [("C123", reply)]
    assert rec["last_seen_reply_ts"] == "999.500000"
    assert (
        rec["reply_poll_backoff_seconds"]
        == helpers["THREAD_REPLY_INITIAL_BACKOFF_SECONDS"]
    )
    assert rec["next_reply_poll_at"] == 1006.0
    assert rec["watch_until"] == 1301.0


def test_a_cloud_conversation_starts_from_the_automation_s_agent_profile(monkeypatch):
    # Arrange
    monkeypatch.setenv("AUTOMATION_AGENT_PROFILE_ID", "0f2b5c2e-6d3a-4e7b-9c1d-2a4b6c8d0e1f")
    helpers = load_slack_monitor_helpers()
    calls = []
    monkeypatch.setitem(
        helpers,
        "_cloud_request",
        lambda method, path, body=None: calls.append((method, path, body)) or {"id": "task-1", "status": "WORKING"},
    )

    # Act
    helpers["_create_cloud_conversation"]("Summarize this thread.", "Slack: #general")

    # Assert
    [(method, path, body)] = calls
    assert (method, path) == ("POST", "/api/v1/app-conversations")
    assert body["agent_profile_id"] == "0f2b5c2e-6d3a-4e7b-9c1d-2a4b6c8d0e1f"


def test_a_cloud_conversation_without_a_profile_leaves_the_choice_to_openhands(monkeypatch):
    # Arrange
    monkeypatch.delenv("AUTOMATION_AGENT_PROFILE_ID", raising=False)
    helpers = load_slack_monitor_helpers()
    calls = []
    monkeypatch.setitem(
        helpers, "_cloud_request", lambda method, path, body=None: calls.append(body) or {"id": "task-1", "status": "WORKING"}
    )

    # Act
    helpers["_create_cloud_conversation"]("Summarize this thread.", "Slack: #general")

    # Assert
    [body] = calls
    assert "agent_profile_id" not in body


def _stored_events(*events: tuple[str, str, str, str]) -> dict:
    """Events-search page, newest first: (id, kind, source, text)."""
    items = []
    for event_id, kind, source, text in events:
        event = {"id": event_id, "kind": kind, "source": source}
        if kind == "ActionEvent":
            event.update(tool_name="finish", action={"message": text})
        else:
            event["llm_message"] = {"content": [{"type": "text", "text": text}]}
        items.append(event)
    return {"items": items}


def test_cloud_final_response_waits_for_the_reply_to_the_latest_message(monkeypatch):
    # Arrange: the follow-up is stored, the agent's answer to it is not yet.
    helpers = load_slack_monitor_helpers()
    page = _stored_events(
        ("user-2", "MessageEvent", "user", "@punk one more"),
        ("finish-1", "ActionEvent", "agent", "First joke"),
        ("user-1", "MessageEvent", "user", "@punk tell me a joke"),
    )
    monkeypatch.setitem(helpers, "_cloud_request", lambda *_args, **_kw: page)

    # Act
    reply = helpers["_cloud_conversation_final_response"]("conv-1")

    # Assert
    assert reply is None


def test_cloud_final_response_returns_the_newest_answer_with_its_event_id(monkeypatch):
    # Arrange
    helpers = load_slack_monitor_helpers()
    page = _stored_events(
        ("finish-2", "ActionEvent", "agent", "Second joke"),
        ("user-2", "MessageEvent", "user", "@punk one more"),
        ("finish-1", "ActionEvent", "agent", "First joke"),
    )
    monkeypatch.setitem(helpers, "_cloud_request", lambda *_args, **_kw: page)

    # Act
    reply = helpers["_cloud_conversation_final_response"]("conv-1")

    # Assert
    assert reply == ("finish-2", "Second joke")


def _completion_harness(monkeypatch, replies: list, clock: list[float]):
    helpers = load_slack_monitor_helpers()
    monkeypatch.setattr(helpers["time"], "time", lambda: clock[0])
    monkeypatch.setitem(helpers, "conversation_status", lambda *_: "finished")
    monkeypatch.setitem(
        helpers, "conversation_final_response", lambda *_: replies.pop(0)
    )
    posted: list[str] = []
    monkeypatch.setitem(
        helpers,
        "post_message",
        lambda _token, _channel, text, thread_ts=None: posted.append(text) or "2.0",
    )
    rec = {
        "conversation_id": "conv-1",
        "channel_id": "C123",
        "thread_ts": "1.0",
        "last_activity": 0.0,
        "llm_profile": "default",
        "llm_model": "test-model",
        "posted_response_event_id": "finish-1",
    }

    def check():
        helpers["_check_conversation_completion"](
            "C123:1.0", rec, "http://agent", "key", "xoxb-test", []
        )

    return check, posted, rec


def test_a_followup_does_not_repost_the_previous_answer(monkeypatch):
    # Arrange: the conversation reports finished before the new answer is
    # stored, so the newest stored answer is still the one already posted.
    clock = [100.0]
    check, posted, rec = _completion_harness(
        monkeypatch,
        [("finish-1", "First joke"), ("finish-2", "Second joke")],
        clock,
    )

    # Act
    check()
    clock[0] = 115.0
    check()

    # Assert
    assert len(posted) == 1
    assert posted[0].startswith("Second joke")
    assert rec["posted_response_event_id"] == "finish-2"
    assert "final_response_wait_started" not in rec


def test_a_reply_that_never_reaches_the_stored_events_is_not_waited_on_forever(
    monkeypatch,
):
    # Arrange
    clock = [100.0]
    check, posted, _rec = _completion_harness(monkeypatch, [None, None], clock)

    # Act
    check()
    clock[0] = 100.0 + 121.0
    check()

    # Assert
    assert len(posted) == 1
    assert posted[0].startswith("Success (no message available).")
