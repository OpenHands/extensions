#!/usr/bin/env python3
"""
QA Changes Evaluation Script

This script runs when a PR is merged or closed to evaluate how well
the QA validation performed. It creates an evaluation trace in Laminar
that can be processed by a signal to determine QA effectiveness.

The evaluation flow:
1. Read the original trace ID from the artifact
2. Fetch PR comments and QA report from GitHub
3. Fetch the final patch/diff
4. Create an evaluation span with all context
5. Score the original trace based on engagement

Environment Variables:
    LMNR_PROJECT_API_KEY: Laminar project API key (required)
    GITHUB_TOKEN: GitHub token for API access (required)
    PR_NUMBER: Pull request number (required)
    REPO_NAME: Repository name in format owner/repo (required)
    PR_MERGED: Whether the PR was merged ('true' or 'false')
"""

import json
import logging
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from lmnr import Laminar, LaminarClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _get_required_env(name: str) -> str:
    """Get a required environment variable or raise an error."""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


def _get_github_headers() -> dict[str, str]:
    """Get headers for GitHub API requests."""
    token = _get_required_env("GITHUB_TOKEN")
    return {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get_agent_usernames() -> set[str]:
    """Get the set of agent usernames to identify agent comments.

    Configurable via AGENT_USERNAMES environment variable (comma-separated).
    Defaults to 'openhands-agent,all-hands-bot'.
    """
    usernames = os.getenv("AGENT_USERNAMES", "openhands-agent,all-hands-bot")
    return set(name.strip() for name in usernames.split(",") if name.strip())


def _handle_github_api_error(e: urllib.error.HTTPError, context: str) -> None:
    """Handle GitHub API errors with rate limit awareness."""
    if e.code == 429:
        retry_after = e.headers.get("Retry-After", "60")
        logger.warning(f"Rate limited by GitHub API. Retry after {retry_after}s")
    logger.error(f"Failed to {context}: HTTP {e.code}")


def fetch_pr_issue_comments(repo: str, pr_number: str) -> list[dict]:
    """Fetch issue-style comments on a PR (the main thread)."""
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    request = urllib.request.Request(url, headers=_get_github_headers())
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        _handle_github_api_error(e, "fetch issue comments")
        return []


def fetch_pr_diff(repo: str, pr_number: str) -> str:
    """Fetch the final diff of the PR."""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers = _get_github_headers()
    headers["Accept"] = "application/vnd.github.v3.diff"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        _handle_github_api_error(e, "fetch PR diff")
        return ""


def fetch_pr_info(repo: str, pr_number: str) -> dict:
    """Fetch PR metadata."""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    request = urllib.request.Request(url, headers=_get_github_headers())
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        _handle_github_api_error(e, "fetch PR info")
        return {}


def extract_qa_report(issue_comments: list[dict]) -> list[dict]:
    """Extract QA report comments made by the agent.

    QA reports are posted as issue comments (via `gh pr comment`).
    """
    agent_users = _get_agent_usernames()
    qa_comments = []

    for comment in issue_comments:
        if comment.get("user", {}).get("login") in agent_users:
            qa_comments.append(
                {
                    "type": "qa_report",
                    "id": comment.get("id"),
                    "body": comment.get("body", ""),
                    "created_at": comment.get("created_at"),
                }
            )

    return qa_comments


def extract_human_responses(
    issue_comments: list[dict],
    agent_users: set[str] | None = None,
) -> list[dict]:
    """Extract comments/responses from humans (non-agent users)."""
    if agent_users is None:
        agent_users = _get_agent_usernames()

    human_responses = []
    for comment in issue_comments:
        if comment.get("user", {}).get("login") not in agent_users:
            human_responses.append(
                {
                    "type": "issue_comment",
                    "user": comment.get("user", {}).get("login"),
                    "body": comment.get("body", ""),
                    "created_at": comment.get("created_at"),
                }
            )

    return human_responses


def truncate_text(text: str, max_chars: int = 50000) -> str:
    """Truncate text to stay within reasonable API payload limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n... [truncated, {len(text)} total chars]"


def load_trace_info(trace_file_path: str | None = None) -> dict:
    """Load trace info from artifact file."""
    trace_info_path = (
        Path(trace_file_path)
        if trace_file_path
        else Path("laminar_trace_info.json")
    )

    if not trace_info_path.exists():
        logger.warning(
            "No trace info file found - evaluation will create standalone trace"
        )
        return {}

    with open(trace_info_path) as f:
        data = json.load(f)

    logger.info(f"Original trace ID: {data.get('trace_id')}")
    if data.get("span_context"):
        logger.info("Found span context - will add evaluation to original trace")
    else:
        logger.info("No span context - evaluation will create standalone trace")

    return data


def fetch_pr_data(repo: str, pr_number: str) -> dict:
    """Fetch all PR data from GitHub relevant to QA evaluation."""
    logger.info("Fetching PR data from GitHub...")

    issue_comments = fetch_pr_issue_comments(repo, pr_number)
    final_diff = fetch_pr_diff(repo, pr_number)
    pr_info = fetch_pr_info(repo, pr_number)

    logger.info(f"Found {len(issue_comments)} issue comments")

    qa_comments = extract_qa_report(issue_comments)
    human_responses = extract_human_responses(issue_comments)

    logger.info(f"Agent made {len(qa_comments)} QA comments")
    logger.info(f"Humans made {len(human_responses)} responses")

    return {
        "issue_comments": issue_comments,
        "final_diff": final_diff,
        "pr_info": pr_info,
        "qa_comments": qa_comments,
        "human_responses": human_responses,
    }


SCORE_QA_POSTED = 0.3  # Agent produced at least one QA report
SCORE_RESPONSE_MAX = 0.2  # Humans engaged with the report (scaled by ratio)
SCORE_PR_MERGED = 0.3  # PR was ultimately merged


def calculate_engagement_score(
    qa_comments: list[dict],
    human_responses: list[dict],
    pr_merged: bool,
) -> float:
    """Calculate engagement score based on interaction metrics.

    Components (max total 0.8):
    - QA report posted: SCORE_QA_POSTED (0.3)
    - Response ratio: up to SCORE_RESPONSE_MAX (0.2)
    - Completion bonus: SCORE_PR_MERGED (0.3)
    """
    score = 0.0
    if qa_comments:
        score += SCORE_QA_POSTED
        if human_responses:
            engagement_ratio = min(len(human_responses) / len(qa_comments), 1.0)
            score += engagement_ratio * SCORE_RESPONSE_MAX
    if pr_merged:
        score += SCORE_PR_MERGED
    return score


def create_evaluation_span(
    pr_number: str,
    repo_name: str,
    pr_merged: bool,
    pr_data: dict,
    trace_info: dict,
) -> str | None:
    """Create Laminar evaluation span and return trace ID."""
    Laminar.initialize()

    evaluation_context = {
        "pr_number": pr_number,
        "repo_name": repo_name,
        "pr_merged": pr_merged,
        "pr_title": pr_data["pr_info"].get("title", ""),
        "pr_state": pr_data["pr_info"].get("state", ""),
        "original_trace_id": trace_info.get("trace_id"),
        "qa_comments": pr_data["qa_comments"],
        "human_responses": pr_data["human_responses"],
        "final_diff": truncate_text(pr_data["final_diff"]),
        "total_issue_comments": len(pr_data["issue_comments"]),
    }

    with Laminar.start_as_current_span(
        name="qa_changes_evaluation",
        input=evaluation_context,
        tags=["qa-changes-evaluation"],
        parent_span_context=trace_info.get("span_context"),
    ):
        Laminar.set_trace_metadata(
            {
                "original_trace_id": trace_info.get("trace_id") or "none",
                "evaluation_type": "qa_changes_effectiveness",
                "pr_number": pr_number,
                "repo_name": repo_name,
                "pr_merged": str(pr_merged),
            }
        )

        summary = {
            "pr": f"{repo_name}#{pr_number}",
            "merged": pr_merged,
            "qa_comments_count": len(pr_data["qa_comments"]),
            "human_responses_count": len(pr_data["human_responses"]),
            "diff_length": len(pr_data["final_diff"]),
        }
        logger.info(f"Evaluation summary: {json.dumps(summary)}")

        Laminar.set_span_output(
            {
                "summary": summary,
                "ready_for_signal": True,
            }
        )

        eval_trace_id = Laminar.get_trace_id()

    Laminar.flush()
    return str(eval_trace_id) if eval_trace_id else None


def main(trace_file_path: str | None = None):
    """Run the QA changes evaluation."""
    logger.info("Starting QA changes evaluation...")

    pr_number = _get_required_env("PR_NUMBER")
    repo_name = _get_required_env("REPO_NAME")
    pr_merged = os.getenv("PR_MERGED", "false").lower() == "true"

    logger.info(f"Evaluating QA for PR #{pr_number} in {repo_name}")
    logger.info(f"PR was merged: {pr_merged}")

    trace_info = load_trace_info(trace_file_path)
    pr_data = fetch_pr_data(repo_name, pr_number)
    eval_trace_id = create_evaluation_span(
        pr_number, repo_name, pr_merged, pr_data, trace_info
    )

    original_trace_id = trace_info.get("trace_id")
    qa_comments = pr_data["qa_comments"]
    human_responses = pr_data["human_responses"]

    # Score engagement on the original trace for immediate feedback
    if original_trace_id:
        try:
            client = LaminarClient()
            engagement_score = calculate_engagement_score(
                qa_comments, human_responses, pr_merged
            )

            client.evaluators.score(
                name="qa_engagement",
                trace_id=original_trace_id,
                score=engagement_score,
                metadata={
                    "qa_comments": len(qa_comments),
                    "human_responses": len(human_responses),
                    "pr_merged": pr_merged,
                    "score_type": "engagement",
                },
            )
            logger.info(
                f"Added engagement score {engagement_score:.2f} "
                f"to original trace {original_trace_id}"
            )

            client.tags.tag(original_trace_id, ["evaluated", f"pr-{pr_number}"])
            logger.info(f"Tagged original trace {original_trace_id}")

        except Exception as e:
            logger.warning(f"Failed to score original trace: {e}")

    # Print evaluation summary
    print("\n=== QA Changes Evaluation ===")
    print(f"PR: {repo_name}#{pr_number}")
    print(f"Merged: {pr_merged}")
    print(f"QA Comments: {len(qa_comments)}")
    print(f"Human Responses: {len(human_responses)}")
    if original_trace_id:
        print(f"Original QA Trace: {original_trace_id}")
    if eval_trace_id:
        print(f"Evaluation Trace: {eval_trace_id}")

    logger.info("QA changes evaluation completed successfully")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate QA changes effectiveness"
    )
    parser.add_argument(
        "--trace-file",
        help="Path to trace info JSON file (default: laminar_trace_info.json)",
    )
    args = parser.parse_args()

    try:
        main(trace_file_path=args.trace_file)
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        sys.exit(1)
