"""Deterministic event automation. No model, repository, or arbitrary task execution."""

import hashlib
import json
import os
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

TITLE = "OpenHands Teams inbound verification"
TEXT = "Synthetic demo: TEAMS-INBOUND-001 was received and processed by an OpenHands event automation. No AI task or repository change was performed."
FOOTER = "Webhook round trip only. Conversational follow-ups are outside this demo."
SECRET_NAME = "TEAMS_INBOUND_DEMO_WEBHOOK_URL"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def get_secret(name):
    url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    if url:
        secret_url = f"{url}/api/settings/secrets/{name}"
    else:
        cloud_url = os.environ["OPENHANDS_CLOUD_API_URL"].rstrip("/")
        sandbox_id = os.environ["SANDBOX_ID"]
        secret_url = (
            f"{cloud_url}/api/v1/sandboxes/{sandbox_id}/settings/secrets/{name}"
        )
    key = os.environ.get("SESSION_API_KEY") or os.environ.get(
        "OH_SESSION_API_KEYS_0", ""
    )
    with urllib.request.urlopen(
        urllib.request.Request(secret_url, headers={"X-Session-API-Key": key}),
        timeout=15,
    ) as response:
        return response.read().decode().strip()


def fire_callback(status="COMPLETED", error=None):
    url = os.environ.get("AUTOMATION_CALLBACK_URL", "")
    if not url:
        return
    body = {"status": status, "run_id": os.environ.get("AUTOMATION_RUN_ID", "")}
    if error:
        body["error"] = error
    with urllib.request.urlopen(
        urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.environ.get('AUTOMATION_CALLBACK_API_KEY', '')}",
            },
        ),
        timeout=15,
    ) as response:
        response.read()


class CommandText(HTMLParser):
    """Extract the command while ignoring Teams' <at> mention elements."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.in_mention = False

    def handle_starttag(self, tag, attrs):
        if tag == "at":
            self.in_mention = True

    def handle_endtag(self, tag):
        if tag == "at":
            self.in_mention = False
        self.parts.append(" ")

    def handle_data(self, data):
        if not self.in_mention:
            self.parts.append(data)


def validate(context):
    # Automation wraps the original Teams activity in event.payload.
    activity = context.get("event", {}).get("payload", {})
    parser = CommandText()
    parser.feed(activity.get("text", ""))
    command = " ".join("".join(parser.parts).split())
    activity_id = activity.get("id")
    conversation_id = activity.get("conversation", {}).get("id")
    if (
        activity.get("type") != "message"
        or command != "verify TEAMS-INBOUND-001"
        or not isinstance(activity_id, str)
        or not activity_id.strip()
        or not isinstance(conversation_id, str)
        or not conversation_id.strip()
    ):
        raise ValueError("unexpected demo event")
    # Match the source's conversation-scoped delivery identity. Hash it so
    # provider identifiers never become filenames or run output.
    return hashlib.sha256(
        json.dumps([conversation_id, activity_id]).encode()
    ).hexdigest()


def card():
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.2",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": TITLE,
                            "weight": "Bolder",
                            "wrap": True,
                        },
                        {"type": "TextBlock", "text": TEXT, "wrap": True},
                        {
                            "type": "TextBlock",
                            "text": FOOTER,
                            "isSubtle": True,
                            "wrap": True,
                        },
                    ],
                },
            }
        ],
    }


def run():
    request_id = validate(json.loads(os.environ.get("AUTOMATION_EVENT_PAYLOAD", "{}")))
    callback = get_secret(SECRET_NAME)
    parsed = urlparse(callback)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or not any(
            (parsed.hostname or "").endswith(suffix)
            for suffix in (".environment.api.powerplatform.com", ".logic.azure.com")
        )
    ):
        raise ValueError("invalid Teams callback host")
    # Reserve before sending. On a local persistent backend, repeating the same
    # activity/run cannot silently post another card. An uncertain send is never
    # retried; inspect the Workflow run and receipt before choosing recovery.
    root = Path.home() / ".openhands" / "teams-inbound-demo-receipts"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    receipt = root / (request_id + ".json")
    state = {"request_id": request_id, "synthetic": True, "state": "reserved"}
    descriptor = os.open(receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        json.dump(state, output)
    try:
        request = urllib.request.Request(
            callback,
            data=json.dumps(card()).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.build_opener(NoRedirect).open(
            request, timeout=20
        ) as response:
            state.update(state="accepted_unverified", http_status=response.status)
            response.read(65536)
    except Exception:
        state["state"] = "uncertain"
        raise RuntimeError("Teams delivery requires reconciliation") from None
    finally:
        receipt.write_text(json.dumps(state))
    # Only sanitized synthetic evidence appears in run output.
    print(json.dumps({"test_id": "TEAMS-INBOUND-001", **state}))


if __name__ == "__main__":
    try:
        run()
    except Exception:
        print("Demo automation failed; inspect private receipt. No automatic retry.")
        fire_callback("FAILED", "Demo verification failed; inspect private receipt")
        raise SystemExit(1)
    else:
        fire_callback()
