"""Tests for the script that sets up the Jira webhook of an event-based automation.

The script talks to two services over HTTPS: the OpenHands automation API and
Jira Cloud. Each test runs it as the entrypoint it is, with `urlopen` replaced by
one in-process stand-in for both services that keeps what they would store.
"""

import hashlib
import hmac
import io
import json
import runpy
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).parent.parent
    / "skills"
    / "jira-issue-to-pr"
    / "scripts"
    / "setup_webhook.py"
)
OPENHANDS = "https://openhands.example.test"
JIRA = "https://acme.atlassian.net"
WEBHOOK_URL = f"{OPENHANDS}/api/automation/v1/events/org-1/jira"


class Services:
    """What the OpenHands automation API and Jira Cloud hold, and how they answer."""

    def __init__(self):
        self.jira_admin = True
        self.jira_rejects_writes = False
        self.openhands_webhook = None  # includes its "secret"
        self.jira_webhooks = {}  # id -> webhook, including its "secret"
        self.writes = []
        self.delivered = []

    def urlopen(self, request, timeout=None):
        method, url = request.get_method(), request.full_url
        body = json.loads(request.data) if request.data else None
        if method != "GET" and "/events/" not in url:
            self.writes.append((method, url))
        status, payload = self._answer(method, url, body, request)
        if status >= 400:
            raise urllib.error.HTTPError(
                url, status, "error", {}, io.BytesIO(json.dumps(payload).encode())
            )
        return _Response(status, payload)

    def _answer(self, method, url, body, request):
        if url == WEBHOOK_URL:
            signature = "sha256=" + hmac.new(
                self.openhands_webhook["secret"].encode(), request.data, hashlib.sha256
            ).hexdigest()
            if request.get_header("X-hub-signature") != signature:
                return 401, {"detail": "Invalid signature"}
            self.delivered.append(body)
            return 200, {"received": True, "matched": 0}
        if url.startswith(OPENHANDS):
            return self._openhands(method, url, body)
        return self._jira(method, url, body)

    def _openhands(self, method, url, body):
        def public():
            return {k: v for k, v in self.openhands_webhook.items() if k != "secret"}

        if method == "GET":
            return 200, {"webhooks": [public()] if self.openhands_webhook else []}
        if url.endswith("/rotate-secret"):
            self.openhands_webhook["secret"] = "rotated-" + "r" * 32
            return 200, {"webhook_secret": self.openhands_webhook["secret"]}
        if method == "PATCH":
            self.openhands_webhook.update(body)
            return 200, public()
        self.openhands_webhook = {
            "id": "webhook-1",
            "enabled": True,
            "webhook_url": WEBHOOK_URL,
            "secret": body.pop("webhook_secret"),
            **body,
        }
        return 201, {**public(), "webhook_secret": None}

    def _jira(self, method, url, body):
        if "/mypermissions" in url:
            return 200, {
                "permissions": {"ADMINISTER": {"havePermission": self.jira_admin}}
            }
        if method != "GET" and self.jira_rejects_writes:
            return 400, {"messages": ["rejected", (body or {}).get("secret")]}
        hook_id = url.rsplit("/", 1)[-1]
        if method == "GET":
            return 200, [
                {**hook, "self": f"{JIRA}/rest/webhooks/1.0/webhook/{i}"}
                for i, hook in self.jira_webhooks.items()
            ]
        if method == "DELETE":
            del self.jira_webhooks[hook_id]
            return 204, {}
        if method == "PUT":
            # Jira keeps the secret of a webhook updated without one.
            kept = self.jira_webhooks[hook_id].get("secret")
            self.jira_webhooks[hook_id] = {"secret": kept, **body}
        else:
            hook_id = "71"
            self.jira_webhooks[hook_id] = body
        return 200, {**body, "self": f"{JIRA}/rest/webhooks/1.0/webhook/{hook_id}"}


class _Response:
    def __init__(self, status, payload):
        self.status = status
        self._raw = json.dumps(payload).encode()

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def services(monkeypatch):
    services = Services()
    monkeypatch.setattr(urllib.request, "urlopen", services.urlopen)
    monkeypatch.setenv("OPENHANDS_API_KEY", "openhands-key")
    monkeypatch.setenv("JIRA_ADMIN_TOKEN", "jira-token")
    return services


@pytest.fixture
def run_script(monkeypatch, capsys):
    """Run the script with the given action and flags; return (exit code, output)."""

    def run(*args):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                str(SCRIPT_PATH),
                *args,
                *("--jira-base-url", JIRA, "--jira-email", "alice@acme.com"),
                *("--jira-token-env", "JIRA_ADMIN_TOKEN"),
                *("--openhands-host", OPENHANDS),
            ],
        )
        code = 0
        try:
            runpy.run_path(str(SCRIPT_PATH), run_name="__main__")
        except SystemExit as exit_:
            code = exit_.code or 0
        captured = capsys.readouterr()
        return code, captured.out + captured.err

    return run


def test_apply_registers_the_webhook_on_both_sides_with_one_secret(
    services, run_script
):
    # Act
    code, _ = run_script("apply")

    # Assert
    assert code == 0
    [jira_webhook] = services.jira_webhooks.values()
    assert jira_webhook["url"] == WEBHOOK_URL
    assert jira_webhook["events"] == ["jira:issue_created", "jira:issue_updated"]
    assert jira_webhook["filters"] == {
        "issue-related-events-section": 'labels = "create-pr"'
    }
    assert jira_webhook["secret"] == services.openhands_webhook["secret"]


def test_apply_registers_the_openhands_webhook_the_way_jira_signs(
    services, run_script
):
    # Act
    run_script("apply")

    # Assert
    assert services.openhands_webhook["signature_header"] == "X-Hub-Signature"
    assert services.openhands_webhook["event_key_expr"] == "webhookEvent"


def test_apply_proves_the_pair_with_a_signed_delivery_that_starts_nothing(
    services, run_script
):
    # Act
    _, output = run_script("apply")

    # Assert
    assert json.loads(output)["signed_delivery_check"] == "ok"
    assert services.delivered == [{"webhookEvent": "openhands:setup_check"}]


def test_apply_never_prints_the_signing_secret(services, run_script):
    # Act
    _, output = run_script("apply")

    # Assert
    assert services.openhands_webhook["secret"] not in output


def test_applying_again_updates_jira_and_keeps_the_secret(services, run_script):
    # Arrange
    run_script("apply")
    secret = services.openhands_webhook["secret"]

    # Act
    code, _ = run_script("apply", "--label", "needs-pr")

    # Assert
    assert code == 0
    [jira_webhook] = services.jira_webhooks.values()
    assert jira_webhook["filters"] == {
        "issue-related-events-section": 'labels = "needs-pr"'
    }
    assert jira_webhook["secret"] == secret == services.openhands_webhook["secret"]


def test_a_failed_jira_update_leaves_the_existing_secret_working(services, run_script):
    # Arrange
    run_script("apply")
    secret = services.openhands_webhook["secret"]
    services.jira_rejects_writes = True

    # Act
    code, _ = run_script("apply", "--label", "needs-pr")

    # Assert
    assert code == 1
    [jira_webhook] = services.jira_webhooks.values()
    assert jira_webhook["secret"] == secret == services.openhands_webhook["secret"]


def test_rotate_secret_gives_both_sides_a_new_secret(services, run_script):
    # Arrange
    run_script("apply")
    secret = services.openhands_webhook["secret"]

    # Act
    code, _ = run_script("apply", "--rotate-secret")

    # Assert
    assert code == 0
    [jira_webhook] = services.jira_webhooks.values()
    assert services.openhands_webhook["secret"] != secret
    assert jira_webhook["secret"] == services.openhands_webhook["secret"]


def test_a_jira_error_that_echoes_the_secret_is_redacted(services, run_script):
    # Arrange
    services.jira_rejects_writes = True

    # Act
    code, output = run_script("apply")

    # Assert
    assert code == 1
    assert services.openhands_webhook["secret"] not in output


def test_an_account_that_is_not_a_jira_administrator_changes_nothing(
    services, run_script
):
    # Arrange
    services.jira_admin = False

    # Act
    code, output = run_script("apply")

    # Assert - exit code 3 is what tells the skill to fall back to manual setup
    assert code == 3
    assert "Administer Jira" in output
    assert services.writes == []


def test_a_dry_run_changes_nothing(services, run_script):
    # Act
    code, output = run_script("apply", "--dry-run")

    # Assert
    assert code == 0
    assert json.loads(output)["jira_webhook"] == "create"
    assert services.writes == []


def test_delete_removes_the_jira_webhook_and_keeps_the_openhands_one(
    services, run_script
):
    # Arrange
    run_script("apply")

    # Act
    code, _ = run_script("delete")

    # Assert
    assert code == 0
    assert services.jira_webhooks == {}
    assert services.openhands_webhook is not None
