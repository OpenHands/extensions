"""Live smoke tests for the daily-workflow integrations (OSS-5193).

These tests exercise the published catalog entries for GitHub, Linear, and
Slack against the real services, through the same client stack
(``openhands.sdk.mcp.create_mcp_tools``) that backs the agent-server's
``POST /api/mcp/test`` probe behind Agent Canvas's Test connection.

Every test is skipped unless real credentials are present in the environment,
so credential-less CI runs them as skips with zero network access. To run
live:

    GITHUB_PERSONAL_ACCESS_TOKEN=... \
    LINEAR_API_KEY=... \
    SLACK_BOT_TOKEN=... SLACK_TEAM_ID=... \
    uv run --group test pytest tests/test_live_integration_smoke.py -rA -s

Preconditions:
- The GitHub token needs the scopes stated in the catalog entry (classic:
  ``repo`` and ``read:user``).
- The Linear API key needs at least read access.
- The Slack bot must be a member of at least one channel with message history
  (``/invite @your-bot``), and its token needs the scopes stated in the
  catalog entry.

Evidence lines are printed as ``[OSS-5193] ...`` and contain only tool names,
counts, and provider error codes — never credentials or message content.
"""

import json
import os
from contextlib import contextmanager

import mcp.types
import pytest
from openhands.sdk.mcp import MCPError, MCPServer, MCPTimeoutError, create_mcp_tools

from openhands_extensions import get_integration_catalog_entry_model


GITHUB_TOKEN_ENV = "GITHUB_PERSONAL_ACCESS_TOKEN"
LINEAR_TOKEN_ENV = "LINEAR_API_KEY"
SLACK_ENV_KEYS = ("SLACK_TEAM_ID", "SLACK_BOT_TOKEN")

HTTP_TIMEOUT = 30.0
STDIO_TIMEOUT = 90.0  # a cold `npx -y` run downloads the Slack server first

# Auth failure codes the Agent Canvas interpreter reclassifies as credential
# failures (agent-canvas src/utils/mcp-credential-validation.ts).
SLACK_AUTH_FAILURES = {
    "invalid_auth",
    "not_authed",
    "account_inactive",
    "token_revoked",
    "token_expired",
}

requires_github = pytest.mark.skipif(
    not os.environ.get(GITHUB_TOKEN_ENV),
    reason=f"set {GITHUB_TOKEN_ENV} to run the live GitHub MCP smoke test",
)
requires_linear = pytest.mark.skipif(
    not os.environ.get(LINEAR_TOKEN_ENV),
    reason=f"set {LINEAR_TOKEN_ENV} to run the live Linear MCP smoke test",
)
requires_slack = pytest.mark.skipif(
    not all(os.environ.get(key) for key in SLACK_ENV_KEYS),
    reason=f"set {' and '.join(SLACK_ENV_KEYS)} to run the live Slack MCP smoke test",
)


def _evidence(line):
    print(f"[OSS-5193] {line}")


def _installable_option(entry_id):
    """The option a local Agent Canvas install uses — the GUI filters out
    provider-OAuth options (isLocallyInstallableMcpOption in agent-canvas)."""
    entry = get_integration_catalog_entry_model(entry_id)
    assert entry is not None, f"catalog entry {entry_id!r} missing"
    for option in entry.connectionOptions:
        if option.auth.strategy != "oauth2":
            return option
    raise AssertionError(f"{entry_id}: no locally installable connection option")


def _remote_server(option, token):
    return MCPServer.model_validate(
        {
            "url": option.transport.url,
            "transport": "http",
            "auth": {"strategy": option.auth.strategy, "value": token},
        }
    )


def _stdio_server(option, env):
    return MCPServer.model_validate(
        {
            "transport": "stdio",
            "command": option.transport.command,
            "args": list(option.transport.args),
            "env": env,
        }
    )


@contextmanager
def _connect(server_id, server, timeout):
    """Yield ``(tool_names, call)`` through the same code path as the
    agent-server probe (mcp_router._probe_mcp_server): connect, list tools,
    invoke read-only tools, join TextContent blocks."""
    with create_mcp_tools({server_id: server}, timeout=timeout) as client:
        tool_names = [tool.name for tool in client.tools]

        def call(name, arguments):
            result = client.call_async_from_sync(
                client.call_tool_mcp,
                name=name,
                arguments=arguments,
                timeout=timeout,
            )
            text = "\n".join(
                block.text
                for block in result.content
                if isinstance(block, mcp.types.TextContent)
            )
            return bool(result.isError), text

        yield tool_names, call


def _first_advertised(tool_names, candidates):
    for name, arguments in candidates:
        if name in tool_names:
            return name, arguments
    pytest.fail(
        "none of the candidate tools "
        f"{sorted({name for name, _ in candidates})} are advertised; "
        f"server offers: {sorted(tool_names)}"
    )


@requires_github
def test_github_identity_and_pr_read():
    option = _installable_option("github")
    # The env var doubles as the catalog's secret name; fail loudly on drift.
    assert option.auth.credentialSecretName == GITHUB_TOKEN_ENV
    server = _remote_server(option, os.environ[GITHUB_TOKEN_ENV])

    with _connect("github", server, HTTP_TIMEOUT) as (tool_names, call):
        assert "get_me" in tool_names, (
            "Agent Canvas's credential probe calls get_me; "
            f"server offers: {sorted(tool_names)}"
        )
        is_error, text = call("get_me", {})
        assert not is_error, f"get_me failed: {text}"
        assert "login" in text
        _evidence(f"github: {len(tool_names)} tools; get_me ok (login present)")

        # Representative PR lookup against a merged, permanently public PR in
        # this very repo (OpenHands/extensions#408).
        name, arguments = _first_advertised(
            tool_names,
            [
                (
                    "pull_request_read",
                    {
                        "method": "get",
                        "owner": "OpenHands",
                        "repo": "extensions",
                        "pullNumber": 408,
                    },
                ),
                (
                    "get_pull_request",
                    {"owner": "OpenHands", "repo": "extensions", "pullNumber": 408},
                ),
                (
                    "search_pull_requests",
                    {"query": "repo:OpenHands/extensions is:pr 408"},
                ),
                ("list_pull_requests", {"owner": "OpenHands", "repo": "extensions"}),
            ],
        )
        is_error, text = call(name, arguments)
        if is_error and "pullNumber" in arguments:
            # Tolerate snake_case argument naming on the hosted server.
            arguments = {
                ("pull_number" if key == "pullNumber" else key): value
                for key, value in arguments.items()
            }
            is_error, text = call(name, arguments)
        assert not is_error, f"{name} failed: {text}"
        assert text.strip()
        if "408" in json.dumps(arguments):
            assert "408" in text, f"{name} response does not reference PR 408"
        _evidence(f"github: PR lookup ok via {name}")


@requires_github
def test_github_invalid_token_yields_structured_failure():
    option = _installable_option("github")
    bogus = "github_pat_invalid_oss5193"
    server = _remote_server(option, bogus)

    try:
        with _connect("github-invalid", server, HTTP_TIMEOUT) as (tool_names, call):
            # Some deployments accept the connection and fail on invocation.
            if "get_me" in tool_names:
                is_error, text = call("get_me", {})
            else:
                is_error, text = True, "get_me not advertised"
            assert is_error, "expected an auth failure with an invalid token"
            assert bogus not in text, "failure text must not echo the credential"
            _evidence("github: invalid token -> tool-level error (is_error=true)")
    except MCPTimeoutError:
        pytest.fail("invalid GitHub token should fail fast, not time out")
    except MCPError as exc:
        detail = str(exc.__cause__ or exc.__context__ or exc)
        assert bogus not in detail, "failure text must not echo the credential"
        _evidence(
            "github: invalid token -> connection-stage failure "
            "(Canvas error_kind=connection)"
        )


@requires_linear
def test_linear_teams_and_issue_read():
    option = _installable_option("linear")
    server = _remote_server(option, os.environ[LINEAR_TOKEN_ENV])

    with _connect("linear", server, HTTP_TIMEOUT) as (tool_names, call):
        assert "list_teams" in tool_names, (
            "Agent Canvas's credential probe calls list_teams; "
            f"server offers: {sorted(tool_names)}"
        )
        is_error, text = call("list_teams", {})
        assert not is_error, f"list_teams failed: {text}"
        _evidence(f"linear: {len(tool_names)} tools; list_teams ok")

        name, arguments = _first_advertised(
            tool_names,
            [("list_issues", {"limit": 1}), ("list_my_issues", {"limit": 1})],
        )
        is_error, text = call(name, arguments)
        assert not is_error, f"{name} failed: {text}"
        assert text.strip()
        _evidence(f"linear: issue read ok via {name}")


@requires_linear
def test_linear_invalid_token_yields_structured_failure():
    option = _installable_option("linear")
    bogus = "lin_api_invalid_oss5193"
    server = _remote_server(option, bogus)

    try:
        with _connect("linear-invalid", server, HTTP_TIMEOUT) as (tool_names, call):
            if "list_teams" in tool_names:
                is_error, text = call("list_teams", {})
            else:
                is_error, text = True, "list_teams not advertised"
            assert is_error, "expected an auth failure with an invalid token"
            assert bogus not in text, "failure text must not echo the credential"
            _evidence("linear: invalid token -> tool-level error (is_error=true)")
    except MCPTimeoutError:
        pytest.fail("invalid Linear token should fail fast, not time out")
    except MCPError as exc:
        detail = str(exc.__cause__ or exc.__context__ or exc)
        assert bogus not in detail, "failure text must not echo the credential"
        _evidence(
            "linear: invalid token -> connection-stage failure "
            "(Canvas error_kind=connection)"
        )


@requires_slack
def test_slack_channel_and_thread_read():
    option = _installable_option("slack")
    env_keys = [field.key for field in option.transport.envFields or []]
    assert set(env_keys) == set(SLACK_ENV_KEYS)
    server = _stdio_server(option, {key: os.environ[key] for key in env_keys})

    with _connect("slack", server, STDIO_TIMEOUT) as (tool_names, call):
        for required in (
            "slack_list_channels",
            "slack_get_channel_history",
            "slack_get_thread_replies",
        ):
            assert required in tool_names, (
                f"{required} not advertised; server offers: {sorted(tool_names)}"
            )

        is_error, text = call("slack_list_channels", {"limit": 5})
        assert not is_error, f"slack_list_channels failed: {text}"
        payload = json.loads(text)
        assert payload.get("ok") is True, (
            f"slack_list_channels not ok: {payload.get('error')}"
        )
        channels = payload.get("channels") or []
        assert channels, "no channels visible to the bot"
        _evidence(
            f"slack: {len(tool_names)} tools; list_channels ok "
            f"({len(channels)} channel(s))"
        )

        for channel in channels:
            is_error, text = call(
                "slack_get_channel_history",
                {"channel_id": channel["id"], "limit": 10},
            )
            if is_error:
                continue
            history = json.loads(text)
            if history.get("ok") is not True:
                continue  # e.g. not_in_channel — try the next channel
            for message in history.get("messages") or []:
                ts = message.get("thread_ts") or message.get("ts")
                if not ts:
                    continue
                is_error, text = call(
                    "slack_get_thread_replies",
                    {"channel_id": channel["id"], "thread_ts": ts},
                )
                assert not is_error, f"slack_get_thread_replies failed: {text}"
                replies = json.loads(text)
                assert replies.get("ok") is True, (
                    f"slack_get_thread_replies not ok: {replies.get('error')}"
                )
                _evidence(
                    "slack: channel history + thread read ok "
                    f"({len(replies.get('messages') or [])} message(s) in thread)"
                )
                return
        pytest.fail(
            "no channel with readable message history: invite the bot to a "
            "public channel that has messages (/invite @your-bot) and rerun"
        )


@requires_slack
def test_slack_invalid_token_yields_in_band_error():
    option = _installable_option("slack")
    bogus = "xoxb-invalid-oss5193"
    server = _stdio_server(
        option,
        {"SLACK_TEAM_ID": os.environ["SLACK_TEAM_ID"], "SLACK_BOT_TOKEN": bogus},
    )

    with _connect("slack-invalid", server, STDIO_TIMEOUT) as (tool_names, call):
        # The stdio server starts and lists tools with any token — the exact
        # reason Agent Canvas interprets the in-band payload of a read-only
        # tool call instead of trusting tools/list.
        assert "slack_list_channels" in tool_names
        is_error, text = call("slack_list_channels", {"limit": 1})
        assert bogus not in text, "failure text must not echo the credential"
        payload = json.loads(text)
        assert payload.get("ok") is False
        assert payload.get("error") in SLACK_AUTH_FAILURES, (
            f"unexpected error code {payload.get('error')!r}; Canvas reclassifies "
            f"only {sorted(SLACK_AUTH_FAILURES)} as credential failures"
        )
        _evidence(
            f"slack: invalid token -> in-band ok=false error={payload.get('error')} "
            f"(is_error={is_error})"
        )
