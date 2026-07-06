"""
Slack → Jira Monitor Automation
================================
Polls a Slack channel every N minutes. For each new parent message that
contains TRIGGER_PHRASE, creates a Jira issue, replies to the thread with
the Jira ticket link, and adds a ✅ reaction to the original message.

Customize the CONFIGURATION block below, package as a tarball, and deploy
via the OpenHands automation API. See SKILL.md for the full setup workflow.
"""

import base64
import json
import os
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

# ── CONFIGURATION ────────────────────────────────────────────────────────────
# All values here must be set before deploying.

SLACK_CHANNEL_ID = "C0BFL769U6Q"       # Slack channel ID to monitor
TRIGGER_PHRASE   = "#bug"              # Case-insensitive trigger (e.g. "#bug", "!ticket")
KV_KEY           = "slack_jira_monitor_bugs"  # Unique KV key — change if running multiple instances

JIRA_BASE_URL    = "https://acme.atlassian.net"  # Your Jira Cloud URL (no trailing slash)
JIRA_EMAIL       = "you@example.com"             # Email tied to the JIRA_CLOUD_KEY secret
JIRA_PROJECT     = "KAN"                         # Jira project key
JIRA_ISSUE_TYPE  = "Task"                        # Issue type (Bug, Task, Story — must exist in project)

# ── END CONFIGURATION ─────────────────────────────────────────────────────────


# ---------------------------------------------------------------------------
# Automation boilerplate helpers (do not modify)
# ---------------------------------------------------------------------------

def get_secret(name):
    """Fetch a named secret from the agent server."""
    url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    key = os.environ.get("SESSION_API_KEY") or os.environ.get("OH_SESSION_API_KEYS_0", "")
    req = urllib.request.Request(
        f"{url}/api/settings/secrets/{name}",
        headers={"X-Session-API-Key": key},
    )
    with urllib.request.urlopen(req) as r:
        return r.read().decode().strip()


def fire_callback(status="COMPLETED", error=None):
    """Signal run completion to the automation service."""
    url = os.environ.get("AUTOMATION_CALLBACK_URL", "")
    if not url:
        return
    body = {"status": status, "run_id": os.environ.get("AUTOMATION_RUN_ID", "")}
    if error:
        body["error"] = error
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                url,
                data=json.dumps(body).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {os.environ.get('AUTOMATION_CALLBACK_API_KEY', '')}",
                },
            )
        )
    except Exception as exc:
        print(f"Callback error: {exc}")


# ---------------------------------------------------------------------------
# KV store helpers
# ---------------------------------------------------------------------------

def _kv_base_url():
    callback = os.environ.get("AUTOMATION_CALLBACK_URL", "")
    if callback:
        parsed = urlparse(callback)
        return f"{parsed.scheme}://{parsed.netloc}"
    return "http://localhost:18001"


def kv_get(key, default=None):
    token = os.environ.get("AUTOMATION_KV_TOKEN", "")
    base  = _kv_base_url()
    try:
        req = urllib.request.Request(
            f"{base}/api/automation/v1/kv/{key}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode()).get("value", default)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return default
        raise
    except Exception as exc:
        print(f"KV get error for '{key}': {exc}")
        return default


def kv_set(key, value):
    token = os.environ.get("AUTOMATION_KV_TOKEN", "")
    base  = _kv_base_url()
    req = urllib.request.Request(
        f"{base}/api/automation/v1/kv/{key}",
        data=json.dumps(value).encode(),
        method="PUT",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


# ---------------------------------------------------------------------------
# Slack helpers
# ---------------------------------------------------------------------------

def slack_get(endpoint, token, params=""):
    sep = "&" if "?" in endpoint else "?"
    url = f"https://slack.com/api/{endpoint}{sep}{params}" if params else f"https://slack.com/api/{endpoint}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def slack_post(method, token, payload):
    req = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


# ---------------------------------------------------------------------------
# Jira helpers
# ---------------------------------------------------------------------------

def _jira_auth_header(api_token):
    credentials = f"{JIRA_EMAIL}:{api_token}"
    return "Basic " + base64.b64encode(credentials.encode()).decode()


def _jira_adf_doc(text):
    """Wrap plain text in Atlassian Document Format (ADF) for Jira REST API v3."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    content = [
        {"type": "paragraph", "content": [{"type": "text", "text": para}]}
        for para in paragraphs
    ] or [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]
    return {"type": "doc", "version": 1, "content": content}


def create_jira_issue(summary, description_text, api_token):
    """Create a Jira issue and return (issue_key, browse_url)."""
    payload = {
        "fields": {
            "project":     {"key": JIRA_PROJECT},
            "summary":     summary,
            "description": _jira_adf_doc(description_text),
            "issuetype":   {"name": JIRA_ISSUE_TYPE},
        }
    }
    req = urllib.request.Request(
        f"{JIRA_BASE_URL}/rest/api/3/issue",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": _jira_auth_header(api_token),
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Jira API error {exc.code}: {exc.read().decode()}") from exc
    key = data["key"]
    return key, f"{JIRA_BASE_URL}/browse/{key}"


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------

def extract_summary(message_text):
    """Derive a short Jira summary from the Slack message."""
    text = message_text
    for phrase in (TRIGGER_PHRASE, TRIGGER_PHRASE.upper(), TRIGGER_PHRASE.title()):
        text = text.replace(phrase, "").strip()
    for sep in (".", "!", "?", "\n"):
        idx = text.find(sep)
        if idx > 10:
            text = text[:idx]
            break
    return text[:120].strip() or f"Issue reported via Slack {SLACK_CHANNEL_ID}"


def build_description(message_text, user_id, ts):
    report_date = time.strftime("%Y-%m-%d", time.gmtime(float(ts)))
    return (
        f"Reported by: {user_id}\n"
        f"Date: {report_date}\n"
        f"Source: Slack channel {SLACK_CHANNEL_ID}\n\n"
        f"Original message:\n{message_text}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    slack_token = get_secret("SLACK_BOT_TOKEN")
    jira_token  = get_secret("JIRA_CLOUD_KEY")

    # Ensure the bot is a member of the monitored channel (idempotent)
    slack_post("conversations.join", slack_token, {"channel": SLACK_CHANNEL_ID})

    # Load or initialise the high-water timestamp
    last_ts = kv_get(KV_KEY)
    if last_ts is None:
        last_ts = str(time.time() - 300)  # default: start 5 minutes ago on first run
        print(f"No prior state — starting from {last_ts}")

    print(f"Polling {SLACK_CHANNEL_ID} for messages since {last_ts}")
    resp = slack_get(
        "conversations.history",
        slack_token,
        f"channel={SLACK_CHANNEL_ID}&oldest={last_ts}&limit=100&inclusive=false",
    )
    if not resp.get("ok"):
        raise RuntimeError(f"conversations.history error: {resp.get('error')}")

    messages = resp.get("messages", [])
    print(f"Fetched {len(messages)} message(s)")

    # Keep only new parent messages (not replies, not system events) with the trigger
    triggered = [
        m for m in messages
        if TRIGGER_PHRASE.lower() in m.get("text", "").lower()
        and m.get("type") == "message"
        and not m.get("subtype")
        and not (m.get("thread_ts") and m["thread_ts"] != m["ts"])
    ]
    print(f"Found {len(triggered)} triggered message(s)")

    new_last_ts = last_ts
    for msg in reversed(triggered):   # oldest first
        ts   = msg["ts"]
        text = msg.get("text", "")
        user = msg.get("user", "unknown")
        print(f"  Processing {ts}: {text[:80]!r}")

        summary     = extract_summary(text)
        description = build_description(text, user, ts)

        issue_key, issue_url = create_jira_issue(summary, description, jira_token)
        print(f"  Created {issue_key}: {issue_url}")

        # Thread reply with Jira link
        reply = slack_post("chat.postMessage", slack_token, {
            "channel":   SLACK_CHANNEL_ID,
            "thread_ts": ts,
            "text":      f"🐛 Jira issue filed: *<{issue_url}|{issue_key}>* — {summary}",
        })
        if not reply.get("ok"):
            print(f"  Warning — thread reply failed: {reply.get('error')}")

        # ✅ reaction on the parent message
        reaction = slack_post("reactions.add", slack_token, {
            "channel":   SLACK_CHANNEL_ID,
            "timestamp": ts,
            "name":      "white_check_mark",
        })
        if not reaction.get("ok") and reaction.get("error") != "already_reacted":
            print(f"  Warning — reaction failed: {reaction.get('error')}")

        if float(ts) > float(new_last_ts):
            new_last_ts = ts

    if new_last_ts != last_ts:
        kv_set(KV_KEY, new_last_ts)
        print(f"State saved — last_ts={new_last_ts}")

    print("Done.")
    fire_callback("COMPLETED")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Fatal: {exc}")
        fire_callback("FAILED", str(exc))
        raise
