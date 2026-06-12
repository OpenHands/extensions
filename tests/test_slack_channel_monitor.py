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
    helper_source = source.split("def channel_history", 1)[0]
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
