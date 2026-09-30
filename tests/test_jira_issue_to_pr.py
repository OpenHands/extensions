"""Tests for where the jira-issue-to-pr automation script starts its conversations.

The script runs top to bottom as the automation's entrypoint, so each test runs it
as a subprocess against one stub HTTP server that plays Jira, the automation
service (KV store and completion callback), and either the local agent server or
OpenHands Cloud - whichever the run's environment points at.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT_PATH = ROOT / "skills" / "jira-issue-to-pr" / "scripts" / "main.py"

ISSUE = {
    "key": "ENG-1",
    "fields": {
        "summary": "Add a README",
        "description": None,
        "updated": "2030-01-01T00:00:00.000+0000",
    },
}
# A baseline from before the issue was updated, so the issue counts as new.
STATE = {"processed_keys": [], "first_run_at": "2020-01-01T00:00:00+00:00"}


class StubServer:
    """Records every request and answers it the way the real service would."""

    def __init__(self):
        self.requests = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def _handle(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                stub.requests.append({
                    "method": self.command,
                    "path": self.path,
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                    "body": json.loads(body) if body else None,
                })
                status, payload = stub.respond(self.path)
                data = payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = do_PUT = _handle

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    @staticmethod
    def respond(path):
        if path == "/rest/api/3/search/jql":
            return 200, {"issues": [ISSUE]}
        if path.startswith("/rest/api/3/issue/"):
            return 201, {}
        if path == "/automation/v1/kv/state":
            return 200, {"value": STATE}
        if path.endswith("/settings/secrets/JIRA_CLOUD_KEY"):
            return 200, "jira-token"
        if path == "/api/settings":
            return 200, {"agent_settings": {"llm": {"model": "test-model"}}}
        if path == "/api/conversations":
            return 201, {"id": "local-conversation"}
        if path == "/api/v1/app-conversations":
            return 200, {"id": "start-task", "status": "WORKING"}
        if path == "/callback":
            return 200, {}
        return 404, {}

    def find(self, method, path):
        return [r for r in self.requests if r["method"] == method and r["path"] == path]


@pytest.fixture
def stub():
    server = StubServer()
    yield server
    server.httpd.shutdown()


@pytest.fixture
def run_script(stub, tmp_path):
    def run(env):
        workdir = tmp_path / "run"
        workdir.mkdir()
        shutil.copy(SCRIPT_PATH, workdir / "main.py")
        (workdir / "config.json").write_text(json.dumps({
            "jira_base_url": stub.url,
            "jira_email": "alice@example.test",
            "jira_token_secret": "JIRA_CLOUD_KEY",
        }))
        return subprocess.run(
            [sys.executable, str(workdir / "main.py")],
            env={
                "PATH": os.environ["PATH"],
                "HOME": str(tmp_path),
                "AUTOMATION_CALLBACK_URL": f"{stub.url}/callback",
                "AUTOMATION_RUN_ID": "run-1",
                **env,
            },
            capture_output=True,
            text=True,
            timeout=60,
        )

    return run


def cloud_env(stub):
    return {
        "OPENHANDS_CLOUD_API_URL": stub.url,
        "OPENHANDS_API_KEY": "openhands-key",
        "SANDBOX_ID": "sandbox-1",
        "SESSION_API_KEY": "session-key",
        "AUTOMATION_API_URL": f"{stub.url}/automation",
        "AUTOMATION_KV_TOKEN": "kv-token",
    }


def local_env(stub):
    return {
        "AGENT_SERVER_URL": stub.url,
        "SESSION_API_KEY": "session-key",
        "AUTOMATION_CALLBACK_API_KEY": "callback-key",
        "AUTOMATION_API_URL": f"{stub.url}/automation",
        "AUTOMATION_KV_TOKEN": "kv-token",
    }


def comment_text(comment):
    return comment["body"]["body"]["content"][0]["content"][0]["text"]


def test_a_cloud_run_reads_the_jira_token_from_its_sandbox_secrets(stub, run_script):
    # Arrange
    env = cloud_env(stub)

    # Act
    result = run_script(env)

    # Assert
    assert result.returncode == 0, result.stderr
    [secret] = stub.find("GET", "/api/v1/sandboxes/sandbox-1/settings/secrets/JIRA_CLOUD_KEY")
    assert secret["headers"]["x-session-api-key"] == "session-key"


def test_a_cloud_run_starts_each_conversation_through_openhands_cloud(stub, run_script):
    # Arrange
    env = cloud_env(stub)

    # Act
    result = run_script(env)

    # Assert
    assert result.returncode == 0, result.stderr
    [conversation] = stub.find("POST", "/api/v1/app-conversations")
    assert conversation["headers"]["authorization"] == "Bearer openhands-key"
    assert conversation["body"]["title"] == "[ENG-1] Add a README"
    assert "ENG-1" in conversation["body"]["initial_message"]["content"][0]["text"]
    assert stub.find("POST", "/api/conversations") == []


def test_a_cloud_run_links_the_jira_issue_to_its_conversation(stub, run_script):
    # Arrange
    env = cloud_env(stub)

    # Act
    result = run_script(env)

    # Assert
    assert result.returncode == 0, result.stderr
    [conversation] = stub.find("POST", "/api/v1/app-conversations")
    [comment] = stub.find("POST", "/rest/api/3/issue/ENG-1/comment")
    conversation_id = conversation["body"]["conversation_id"]
    assert comment_text(comment) == f"I'm on it: {stub.url}/canvas/conversations/{conversation_id}"


def test_a_cloud_run_reports_completion_with_its_api_key(stub, run_script):
    # Arrange
    env = cloud_env(stub)

    # Act
    result = run_script(env)

    # Assert
    assert result.returncode == 0, result.stderr
    [callback] = stub.find("POST", "/callback")
    assert callback["headers"]["authorization"] == "Bearer openhands-key"
    assert callback["body"]["status"] == "COMPLETED"


def test_a_cloud_run_without_the_kv_store_fails_before_dispatching(stub, run_script):
    # Arrange
    env = cloud_env(stub)
    del env["AUTOMATION_KV_TOKEN"]

    # Act
    result = run_script(env)

    # Assert
    assert result.returncode == 1
    assert stub.find("POST", "/api/v1/app-conversations") == []
    [callback] = stub.find("POST", "/callback")
    assert callback["body"]["status"] == "FAILED"


def test_a_local_run_still_starts_conversations_on_the_agent_server(stub, run_script):
    # Arrange
    env = local_env(stub)

    # Act
    result = run_script(env)

    # Assert
    assert result.returncode == 0, result.stderr
    [conversation] = stub.find("POST", "/api/conversations")
    assert conversation["headers"]["x-session-api-key"] == "session-key"
    [comment] = stub.find("POST", "/rest/api/3/issue/ENG-1/comment")
    assert comment_text(comment) == f"I'm on it: {stub.url}/conversations/local-conversation"
    assert stub.find("POST", "/api/v1/app-conversations") == []


def test_a_local_run_still_reports_completion_with_its_callback_key(stub, run_script):
    # Arrange
    env = {**local_env(stub), "OPENHANDS_API_KEY": "openhands-key"}

    # Act
    result = run_script(env)

    # Assert
    assert result.returncode == 0, result.stderr
    [callback] = stub.find("POST", "/callback")
    assert callback["headers"]["authorization"] == "Bearer callback-key"
