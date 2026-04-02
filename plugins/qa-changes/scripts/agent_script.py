#!/usr/bin/env python3
"""
QA Changes Agent

This script runs an OpenHands agent to QA a pull request by actually
setting up the environment, running the test suite, exercising the
changed behavior, and posting a structured report as a PR comment.

Unlike the pr-review agent which reads the diff and posts inline code
review comments, the QA agent *executes* the code to verify the change
works as described.

The agent uses the /qa-changes skill for its methodology and posts
results as a PR comment via `gh pr comment`.

Environment Variables:
    LLM_API_KEY: API key for the LLM (required)
    LLM_MODEL: Language model to use (default: anthropic/claude-sonnet-4-5-20250929)
    LLM_BASE_URL: Optional base URL for LLM API
    GITHUB_TOKEN: GitHub token for API access (required)
    PR_NUMBER: Pull request number (required)
    PR_TITLE: Pull request title (required)
    PR_BODY: Pull request body (optional)
    PR_BASE_BRANCH: Base branch name (required)
    PR_HEAD_BRANCH: Head branch name (required)
    REPO_NAME: Repository name in format owner/repo (required)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from openhands.sdk import LLM, Agent, AgentContext, Conversation, get_logger
from openhands.sdk.context.skills import load_project_skills
from openhands.sdk.conversation import get_agent_final_response
from openhands.sdk.git.utils import run_git_command
from openhands.tools.preset.default import get_default_condenser, get_default_tools

# Add the script directory to Python path so we can import prompt.py
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from prompt import format_prompt  # noqa: E402

logger = get_logger(__name__)

# Maximum total diff size (characters)
MAX_TOTAL_DIFF = 100000


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


def _call_github_api(
    url: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    accept: str = "application/vnd.github+json",
) -> Any:
    """Make a GitHub API request."""
    token = _get_required_env("GITHUB_TOKEN")

    if not url.startswith("http"):
        url = f"https://api.github.com{url}"

    request = urllib.request.Request(url, method=method)
    request.add_header("Accept", accept)
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")

    if data:
        request.add_header("Content-Type", "application/json")
        request.data = json.dumps(data).encode("utf-8")

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw_data = response.read()
            if "diff" in accept:
                return raw_data.decode("utf-8", errors="replace")
            return json.loads(raw_data.decode("utf-8"))
    except urllib.error.HTTPError as e:
        details = (e.read() or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"GitHub API request failed: HTTP {e.code} {e.reason}. {details}"
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"GitHub API request failed: {e.reason}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"GitHub API returned invalid JSON: {e}") from e


def get_pr_diff(pr_number: str) -> str:
    """Fetch the PR diff via the GitHub API."""
    repo = _get_required_env("REPO_NAME")
    return _call_github_api(
        f"/repos/{repo}/pulls/{pr_number}",
        accept="application/vnd.github.v3.diff",
    )


def truncate_diff(diff_text: str, max_total: int = MAX_TOTAL_DIFF) -> str:
    if len(diff_text) <= max_total:
        return diff_text
    total_chars = len(diff_text)
    return (
        diff_text[:max_total]
        + f"\n\n... [diff truncated, {total_chars:,} chars total, "
        + f"showing first {max_total:,}] ..."
    )


def get_head_commit_sha(repo_dir: Path | None = None) -> str:
    if repo_dir is None:
        repo_dir = Path.cwd()
    return run_git_command(["git", "rev-parse", "HEAD"], repo_dir).strip()


def validate_environment() -> dict[str, Any]:
    """Validate required environment variables and return config."""
    required_vars = [
        "LLM_API_KEY",
        "GITHUB_TOKEN",
        "PR_NUMBER",
        "PR_TITLE",
        "PR_BASE_BRANCH",
        "PR_HEAD_BRANCH",
        "REPO_NAME",
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)

    return {
        "api_key": os.getenv("LLM_API_KEY"),
        "github_token": os.getenv("GITHUB_TOKEN"),
        "model": os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929"),
        "base_url": os.getenv("LLM_BASE_URL"),
        "pr_info": {
            "number": os.getenv("PR_NUMBER"),
            "title": os.getenv("PR_TITLE"),
            "body": os.getenv("PR_BODY", ""),
            "repo_name": os.getenv("REPO_NAME"),
            "base_branch": os.getenv("PR_BASE_BRANCH"),
            "head_branch": os.getenv("PR_HEAD_BRANCH"),
        },
    }


def create_agent(config: dict[str, Any]) -> Agent:
    """Create and configure the QA agent."""
    llm_config: dict[str, Any] = {
        "model": config["model"],
        "api_key": config["api_key"],
        "usage_id": "qa_changes_agent",
        "drop_params": True,
    }
    if config["base_url"]:
        llm_config["base_url"] = config["base_url"]

    llm = LLM(**llm_config)

    cwd = os.getcwd()
    project_skills = load_project_skills(cwd)
    logger.info(
        f"Loaded {len(project_skills)} project skills: "
        f"{[s.name for s in project_skills]}"
    )

    agent_context = AgentContext(
        load_public_skills=True,
        skills=project_skills,
    )

    return Agent(
        llm=llm,
        tools=get_default_tools(enable_browser=False),
        agent_context=agent_context,
        system_prompt_kwargs={"cli_mode": True},
        condenser=get_default_condenser(
            llm=llm.model_copy(update={"usage_id": "condenser"})
        ),
    )


def run_qa(
    agent: Agent,
    prompt: str,
    secrets: dict[str, str],
) -> Conversation:
    """Execute the QA validation."""
    cwd = os.getcwd()
    conversation = Conversation(
        agent=agent,
        workspace=cwd,
        secrets=secrets,
    )

    logger.info("Starting QA validation...")
    logger.info("Agent will set up environment, run tests, and exercise changes")

    conversation.send_message(prompt)
    conversation.run()

    response = get_agent_final_response(conversation.state.events)
    if response:
        logger.info(f"Agent final response: {len(response)} characters")

    return conversation


def log_cost_summary(conversation: Conversation) -> None:
    """Print cost information for CI output."""
    metrics = conversation.conversation_stats.get_combined_metrics()
    print("\n=== QA Changes Cost Summary ===")
    print(f"Total Cost: ${metrics.accumulated_cost:.6f}")
    if metrics.accumulated_token_usage:
        usage = metrics.accumulated_token_usage
        print(f"Prompt Tokens: {usage.prompt_tokens}")
        print(f"Completion Tokens: {usage.completion_tokens}")
        if usage.cache_read_tokens > 0:
            print(f"Cache Read Tokens: {usage.cache_read_tokens}")
        if usage.cache_write_tokens > 0:
            print(f"Cache Write Tokens: {usage.cache_write_tokens}")


def main():
    """Run the QA agent."""
    logger.info("Starting QA changes process...")

    config = validate_environment()
    pr_info = config["pr_info"]

    logger.info(f"QA for PR #{pr_info['number']}: {pr_info['title']}")

    try:
        pr_diff = truncate_diff(get_pr_diff(pr_info["number"]))
        logger.info(f"Got PR diff with {len(pr_diff)} characters")

        commit_id = get_head_commit_sha()
        logger.info(f"HEAD commit SHA: {commit_id}")

        prompt = format_prompt(
            title=pr_info.get("title", "N/A"),
            body=pr_info.get("body") or "No description provided",
            repo_name=pr_info.get("repo_name", "N/A"),
            base_branch=pr_info.get("base_branch", "main"),
            head_branch=pr_info.get("head_branch", "N/A"),
            pr_number=pr_info["number"],
            commit_id=commit_id,
            diff=pr_diff,
        )

        agent = create_agent(config)

        secrets: dict[str, str] = {}
        if config["api_key"]:
            secrets["LLM_API_KEY"] = config["api_key"]
        if config["github_token"]:
            secrets["GITHUB_TOKEN"] = config["github_token"]

        conversation = run_qa(agent, prompt, secrets)
        log_cost_summary(conversation)

        logger.info("QA validation completed successfully")

    except Exception as e:
        logger.error(f"QA validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
