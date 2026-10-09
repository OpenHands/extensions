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
# A deployment that reaches Jira through the user's connected MCP server.
MCP_CONFIG = {"jira_mcp_server": "atlassian-rovo", "jira_cloud_id": "cloud-1"}
MCP_TOOL_PATH = "/api/v1/mcp/servers/atlassian-rovo/call-tool"
# What the conversation for ISSUE is asked when no git provider is configured. The
# Jira to GitHub PR template relies on this text staying as it is.
GITHUB_PROMPT = """Create a GitHub Pull Request for the following Jira issue.

Jira Issue : ENG-1
Summary    : Add a README
Description: No description provided.

Steps:
1. Find the target GitHub repository in the Description above. Look for a reference in
   "owner/repo" format (e.g. "acme-org/backend") or a full GitHub URL
   (e.g. "https://github.com/acme-org/backend"). Use that repository.
   If no repository is mentioned, create a file `jira/ENG-1/notes.md` with the issue
   details and print a message explaining that no GitHub repo was found in the ticket.
2. Clone the repository (e.g. https://github.com/<owner>/<repo>).
3. Create branch `jira/eng-1` from the default branch.
4. Implement the changes described in the issue.
   If the description is vague or missing, create `jira/ENG-1/notes.md`
   with the issue key, summary, and description as a placeholder.
5. Commit, push the branch, and open a Pull Request:
   - Title : [ENG-1] Add a README
   - Body  : Reference the Jira issue key and describe the changes made.
6. Print the PR URL when done.
"""


class StubServer:
    """Records every request and answers it the way the real service would."""

    def __init__(self):
        self.requests = []
        # What the automation's KV store holds, and the tasks OpenHands Cloud
        # reports for the conversations it was asked to start.
        self.state = dict(STATE)
        self.start_tasks = []
        # Set to make the connected MCP server report a failed tool call.
        self.mcp_error = None
        # The name the connected MCP server offers its comment tool under.
        self.mcp_comment_tool = "addOrEditJiraIssueComment"
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def _handle(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                request = {
                    "method": self.command,
                    "path": self.path,
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                    "body": json.loads(body) if body else None,
                }
                stub.requests.append(request)
                status, payload = stub.respond(self.path, request["body"])
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

    def respond(self, path, body):
        if path == MCP_TOOL_PATH:
            if self.mcp_error:
                return 200, {"is_error": True, "text": self.mcp_error}
            if body["name"] not in ("searchJiraIssuesUsingJql", self.mcp_comment_tool):
                return 200, {"is_error": True, "text": f"Tool {body['name']!r} not advertised by server"}
            found = {"issues": [ISSUE]} if body["name"] == "searchJiraIssuesUsingJql" else {}
            return 200, {"is_error": False, "text": json.dumps(found)}
        if path == "/rest/api/3/search/jql":
            return 200, {"issues": [ISSUE]}
        if path.startswith("/rest/api/3/issue/"):
            return 201, {}
        if path == "/automation/v1/kv/state":
            return 200, {"value": self.state}
        if path.endswith("/settings/secrets/JIRA_CLOUD_KEY"):
            return 200, "jira-token"
        if path == "/api/settings":
            return 200, {"agent_settings": {"llm": {"model": "test-model"}}}
        if path == "/api/conversations":
            return 201, {"id": "local-conversation"}
        if path == "/api/v1/app-conversations":
            return 200, {"id": "start-task", "status": "WORKING"}
        if path.startswith("/api/v1/app-conversations/start-tasks?"):
            return 200, self.start_tasks
        if path == "/callback":
            return 200, {}
        return 404, {}

    def find(self, method, path):
        return [r for r in self.requests if r["method"] == method and r["path"] == path]

    def mcp_calls(self, tool):
        return [r for r in self.find("POST", MCP_TOOL_PATH) if r["body"]["name"] == tool]


@pytest.fixture
def stub():
    server = StubServer()
    yield server
    server.httpd.shutdown()


@pytest.fixture
def run_script(stub, tmp_path):
    def run(env, config=None):
        workdir = tmp_path / "run"
        workdir.mkdir()
        shutil.copy(SCRIPT_PATH, workdir / "main.py")
        (workdir / "config.json").write_text(json.dumps(config or {
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


def prompt_text(conversation):
    return conversation["body"]["initial_message"]["content"][0]["text"]


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


def test_a_cloud_run_starts_an_issue_again_when_its_conversation_failed_to_start(stub, run_script):
    # Arrange - an earlier run asked for the conversation and marked the issue done
    stub.state = {
        **STATE,
        "processed_keys": ["ENG-1"],
        "pending_starts": {"ENG-1": {"task_id": "task-1", "attempts": 1}},
    }
    stub.start_tasks = [{"id": "task-1", "status": "ERROR", "detail": "sandbox did not start"}]

    # Act
    result = run_script(cloud_env(stub))

    # Assert
    assert result.returncode == 0, result.stderr
    [conversation] = stub.find("POST", "/api/v1/app-conversations")
    assert conversation["body"]["title"] == "[ENG-1] Add a README"


def test_a_cloud_run_leaves_an_issue_alone_once_its_conversation_is_up(stub, run_script):
    # Arrange
    stub.state = {
        **STATE,
        "processed_keys": ["ENG-1"],
        "pending_starts": {"ENG-1": {"task_id": "task-1", "attempts": 1}},
    }
    stub.start_tasks = [{"id": "task-1", "status": "READY"}]

    # Act
    result = run_script(cloud_env(stub))

    # Assert
    assert result.returncode == 0, result.stderr
    assert stub.find("POST", "/api/v1/app-conversations") == []
    assert stub.find("POST", "/rest/api/3/issue/ENG-1/comment") == []


def test_a_cloud_run_reports_a_start_that_keeps_failing_on_the_issue(stub, run_script):
    # Arrange - the last allowed attempt has failed as well
    stub.state = {
        **STATE,
        "processed_keys": ["ENG-1"],
        "pending_starts": {"ENG-1": {"task_id": "task-1", "attempts": 3}},
    }
    stub.start_tasks = [{"id": "task-1", "status": "ERROR", "detail": "sandbox did not start"}]

    # Act
    result = run_script(cloud_env(stub))

    # Assert
    assert result.returncode == 0, result.stderr
    assert stub.find("POST", "/api/v1/app-conversations") == []
    [comment] = stub.find("POST", "/rest/api/3/issue/ENG-1/comment")
    assert "could not start a conversation" in comment_text(comment)
    assert "sandbox did not start" in comment_text(comment)


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


def test_a_cloud_run_finds_issues_through_the_connected_mcp_server(stub, run_script):
    # Arrange
    env = cloud_env(stub)

    # Act
    result = run_script(env, MCP_CONFIG)

    # Assert
    assert result.returncode == 0, result.stderr
    [search] = stub.mcp_calls("searchJiraIssuesUsingJql")
    assert search["headers"]["authorization"] == "Bearer openhands-key"
    assert search["body"]["arguments"]["cloudId"] == "cloud-1"
    assert 'labels = "create-pr"' in search["body"]["arguments"]["jql"]
    [conversation] = stub.find("POST", "/api/v1/app-conversations")
    assert conversation["body"]["title"] == "[ENG-1] Add a README"
    assert [r for r in stub.requests if "/settings/secrets/" in r["path"]] == []


def test_a_cloud_run_links_the_jira_issue_through_the_connected_mcp_server(stub, run_script):
    # Arrange
    env = cloud_env(stub)

    # Act
    result = run_script(env, MCP_CONFIG)

    # Assert
    assert result.returncode == 0, result.stderr
    [conversation] = stub.find("POST", "/api/v1/app-conversations")
    [comment] = stub.mcp_calls("addOrEditJiraIssueComment")
    conversation_id = conversation["body"]["conversation_id"]
    assert comment["body"]["arguments"] == {
        "cloudId": "cloud-1",
        "issueIdOrKey": "ENG-1",
        "commentBody": f"I'm on it: {stub.url}/canvas/conversations/{conversation_id}",
    }


def test_a_cloud_run_links_the_jira_issue_when_the_mcp_server_still_has_the_older_comment_tool(stub, run_script):
    # Arrange
    stub.mcp_comment_tool = "addCommentToJiraIssue"

    # Act
    result = run_script(cloud_env(stub), MCP_CONFIG)

    # Assert
    assert result.returncode == 0, result.stderr
    [comment] = stub.mcp_calls("addCommentToJiraIssue")
    assert comment["body"]["arguments"]["issueIdOrKey"] == "ENG-1"
    assert comment["body"]["arguments"]["commentBody"].startswith("I'm on it: ")


def test_a_cloud_run_fails_when_the_connected_mcp_server_reports_an_error(stub, run_script):
    # Arrange
    stub.mcp_error = "The MCP server must be authorized again"

    # Act
    result = run_script(cloud_env(stub), MCP_CONFIG)

    # Assert
    assert result.returncode == 1
    assert stub.find("POST", "/api/v1/app-conversations") == []
    [callback] = stub.find("POST", "/callback")
    assert callback["body"]["status"] == "FAILED"
    assert "must be authorized again" in callback["body"]["error"]


def test_a_cloud_run_asks_for_a_github_pull_request_when_no_provider_is_configured(stub, run_script):
    # Act
    result = run_script(cloud_env(stub), MCP_CONFIG)

    # Assert
    assert result.returncode == 0, result.stderr
    [conversation] = stub.find("POST", "/api/v1/app-conversations")
    assert prompt_text(conversation) == GITHUB_PROMPT


def test_a_cloud_run_asks_for_a_gitlab_merge_request_when_the_provider_is_gitlab(stub, run_script):
    # Act
    result = run_script(cloud_env(stub), {**MCP_CONFIG, "git_provider": "gitlab"})

    # Assert
    assert result.returncode == 0, result.stderr
    [conversation] = stub.find("POST", "/api/v1/app-conversations")
    prompt = prompt_text(conversation)
    assert prompt.startswith("Create a GitLab Merge Request for the following Jira issue.")
    assert '"group/project" format' in prompt
    assert "self-managed" in prompt
    assert "https://gitlab.com/<group>/<project>" in prompt
    assert "Print the MR URL" in prompt
    assert "github.com" not in prompt
    # Without a git credential the conversation delivers through the GitLab MCP tools.
    for tool in ("add_branch", "add_commit", "save_merge_request", "get_repository_file"):
        assert f"`{tool}`" in prompt
    assert "Create branch `jira/eng-1`" in prompt
    assert conversation["body"]["title"] == "[ENG-1] Add a README"


def test_a_cloud_run_asks_for_a_bitbucket_pull_request_when_the_provider_is_bitbucket(stub, run_script):
    # Act
    result = run_script(cloud_env(stub), {**MCP_CONFIG, "git_provider": "bitbucket"})

    # Assert
    assert result.returncode == 0, result.stderr
    [conversation] = stub.find("POST", "/api/v1/app-conversations")
    prompt = prompt_text(conversation)
    assert prompt.startswith("Create a Bitbucket Pull Request for the following Jira issue.")
    assert '"workspace/repo" format' in prompt
    assert "https://bitbucket.org/<workspace>/<repo>" in prompt
    assert "Print the PR URL" in prompt
    assert "Merge Request" not in prompt
    # Without a git credential the conversation delivers through Rovo's Bitbucket tools.
    for tool in (
        "createBitbucketRepoBranch",
        "createBitbucketRepoCommit",
        "createBitbucketRepoPullRequest",
        "getBitbucketRepoFileContent",
    ):
        assert f"`{tool}`" in prompt


def test_a_run_with_an_unknown_git_provider_fails_before_dispatching(stub, run_script):
    # Act
    result = run_script(cloud_env(stub), {**MCP_CONFIG, "git_provider": "gitea"})

    # Assert
    assert result.returncode == 1
    assert stub.find("POST", "/api/v1/app-conversations") == []
    [callback] = stub.find("POST", "/callback")
    assert callback["body"]["status"] == "FAILED"
    assert "git_provider" in callback["body"]["error"]
    assert "gitea" in callback["body"]["error"]


def test_a_local_run_cannot_reach_jira_through_a_connected_mcp_server(stub, run_script):
    # Arrange
    env = local_env(stub)

    # Act
    result = run_script(env, MCP_CONFIG)

    # Assert
    assert result.returncode == 1
    assert stub.find("POST", "/api/conversations") == []
    [callback] = stub.find("POST", "/callback")
    assert callback["body"]["status"] == "FAILED"
    assert "OpenHands Cloud or Enterprise" in callback["body"]["error"]


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
