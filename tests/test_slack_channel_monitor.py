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
    markdown_summary = "✅ Done!\n\n- **Bold:** [link](https://example.com)"

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

