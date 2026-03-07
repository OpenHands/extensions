#!/usr/bin/env python3
"""
GitHub CI Debug Agent

This script runs an OpenHands agent to debug GitHub Actions CI failures.
The agent fetches failed workflow logs, analyzes errors, and provides
actionable fixes.

Environment Variables:
    LLM_API_KEY: API key for the LLM (required)
    LLM_MODEL: Language model to use (default: anthropic/claude-sonnet-4-5-20250929)
    LLM_BASE_URL: Optional base URL for LLM API
    GITHUB_TOKEN: GitHub token for API access (required)
    RUN_ID: Workflow run ID to debug (required)
    REPO_NAME: Repository name in format owner/repo (required)
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from openhands.sdk import LLM, Agent, AgentContext, Conversation, get_logger
    from openhands.sdk.context.skills import load_project_skills
    from openhands.tools.preset.default import (
        get_default_condenser,
        get_default_tools,
    )
    OPENHANDS_IMPORT_ERROR: ModuleNotFoundError | None = None
except ModuleNotFoundError as exc:
    LLM = Agent = AgentContext = Conversation = None
    load_project_skills = get_default_condenser = get_default_tools = None
    OPENHANDS_IMPORT_ERROR = exc

    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from prompt import format_prompt

logger = get_logger(__name__)


def _require_openhands_runtime() -> None:
    """Raise a helpful error when OpenHands runtime deps are unavailable."""
    if OPENHANDS_IMPORT_ERROR is not None:
        raise ModuleNotFoundError(
            "OpenHands runtime dependencies are required to execute this script"
        ) from OPENHANDS_IMPORT_ERROR


# Max characters to keep from logs. Configurable via MAX_LOG_SIZE env var.
# Default keeps ~50k chars which is roughly 12k tokens.
DEFAULT_MAX_LOG_SIZE = 50000


class GHCommandError(Exception):
    """Raised when a GitHub CLI command fails."""

    pass


@dataclass
class Config:
    """Configuration for the CI debug agent."""

    api_key: str
    github_token: str
    model: str
    base_url: str | None
    run_id: str
    repo_name: str


@dataclass
class WorkflowData:
    """Data fetched from GitHub about a workflow run."""

    name: str
    branch: str
    commit_sha: str
    triggered_by: str
    jobs: list[dict]
    failed_jobs_summary: str
    logs: str


def _get_max_log_size() -> int:
    """Get max log size from env or use default."""
    try:
        return int(os.getenv("MAX_LOG_SIZE", DEFAULT_MAX_LOG_SIZE))
    except ValueError:
        return DEFAULT_MAX_LOG_SIZE


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


def _run_gh_command(args: list[str]) -> str | None:
    """Run a GitHub CLI command and return output.

    Returns:
        The command output on success, None on failure (allows callers to
        distinguish between empty output and API failure).

    Raises:
        GHCommandError: When gh CLI is not found (unrecoverable).
    """
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.warning(f"gh command failed: {result.stderr}")
            return None
        return result.stdout
    except subprocess.TimeoutExpired:
        logger.warning("gh command timed out")
        return None
    except FileNotFoundError:
        raise GHCommandError("gh CLI not found - please install GitHub CLI")


def get_workflow_run_info(run_id: str, repo_name: str) -> dict | None:
    """Fetch workflow run information.

    Returns:
        dict on success, None on failure.
    """
    output = _run_gh_command([
        "run", "view", run_id,
        "--repo", repo_name,
        "--json", "name,headBranch,headSha,event,jobs,conclusion,createdAt"
    ])
    if output is None:
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        logger.error("Failed to parse workflow run info")
        return None


# Default error patterns to search for in logs (prioritized by importance)
# Customize by setting ERROR_PATTERNS_FILE env var to a JSON file with a list of patterns.
# Example: ERROR_PATTERNS_FILE=.github/ci-debug-patterns.json
# The JSON file should contain an array of regex patterns:
#   ["(?i)cargo.*error", "(?i)go:.*cannot", "(?i)your-custom-pattern"]
DEFAULT_ERROR_PATTERNS = [
    r"(?i)error[:\s]",
    r"(?i)failed[:\s]",
    r"(?i)exception[:\s]",
    r"(?i)traceback",
    r"(?i)fatal[:\s]",
    r"(?i)exit code [1-9]",
    r"(?i)ENOENT",
    r"(?i)permission denied",
    r"(?i)not found",
]


def _load_error_patterns() -> list[str]:
    """Load error patterns from file or use defaults.

    Environment variable ERROR_PATTERNS_FILE can point to a JSON file
    containing custom patterns for project-specific error detection.
    """
    patterns_file = os.getenv("ERROR_PATTERNS_FILE")
    if patterns_file:
        try:
            with open(patterns_file) as f:
                custom_patterns = json.load(f)
            if isinstance(custom_patterns, list):
                logger.info(f"Loaded {len(custom_patterns)} custom error patterns")
                return custom_patterns
            logger.warning("Invalid patterns file format, using defaults")
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load patterns file: {e}, using defaults")
    return DEFAULT_ERROR_PATTERNS


def _compile_error_patterns(patterns: list[str]) -> list[re.Pattern[str]]:
    """Compile regex patterns once before scanning logs."""
    compiled_patterns: list[re.Pattern[str]] = []
    for pattern in patterns:
        try:
            compiled_patterns.append(re.compile(pattern))
        except re.error as exc:
            logger.warning(f"Skipping invalid error pattern {pattern!r}: {exc}")
    return compiled_patterns


def _find_error_context(
    logs: str,
    max_size: int,
    error_patterns: list[str] | None = None,
) -> str | None:
    """Extract context around error patterns in logs.

    Strategy:
    1. Search for common error patterns (configurable via ERROR_PATTERNS_FILE)
    2. If found, extract context around the first significant error
    3. Fall back to head/tail truncation if no patterns found
    """
    lines = logs.split("\n")
    compiled_patterns = _compile_error_patterns(
        error_patterns if error_patterns is not None else _load_error_patterns()
    )

    # Find lines containing error patterns
    error_indices = []
    for i, line in enumerate(lines):
        for pattern in compiled_patterns:
            if pattern.search(line):
                error_indices.append(i)
                break

    if error_indices:
        # Focus on first error with surrounding context
        first_error = error_indices[0]
        # Calculate how much context we can include
        total_lines = len(lines)
        # Estimate avg line length for context calculation
        avg_line_len = len(logs) // max(total_lines, 1)
        context_lines = max_size // max(avg_line_len, 50)

        # Get context: 20% before error, 80% after (errors cascade down)
        before_context = int(context_lines * 0.2)
        after_context = context_lines - before_context

        start = max(0, first_error - before_context)
        end = min(total_lines, first_error + after_context)

        extracted_lines = lines[start:end]
        extracted = "\n".join(extracted_lines)

        if len(extracted) > max_size:
            # Still too big, do a final trim
            extracted = extracted[:max_size]

        truncation_note = ""
        if start > 0 or end < total_lines:
            truncation_note = (
                f"\n[Context extracted around error at line {first_error + 1}. "
                f"Original log: {total_lines} lines]\n\n"
            )
        return truncation_note + extracted

    # No error patterns found - fall back to head/tail
    return None


def _truncate_logs(logs: str, max_size: int) -> str:
    """Truncate logs intelligently, preserving error context."""
    # Try context-aware truncation first
    context_result = _find_error_context(logs, max_size)
    if context_result:
        return context_result

    # Fall back to head/tail truncation (40% head, 60% tail)
    first_chunk = int(max_size * 0.4)
    last_chunk = max_size - first_chunk
    truncated_chars = len(logs) - max_size
    return (
        logs[:first_chunk] +
        f"\n\n[... {truncated_chars:,} characters truncated ...]\n\n" +
        logs[-last_chunk:]
    )


def get_failed_job_logs(run_id: str, repo_name: str) -> str | None:
    """Fetch logs from failed jobs.

    If logs exceed MAX_LOG_SIZE, uses context-aware truncation:
    1. Searches for error patterns and extracts surrounding context
    2. Falls back to head/tail truncation if no patterns found

    Returns:
        Logs string on success, None on failure.
    """
    output = _run_gh_command([
        "run", "view", run_id,
        "--repo", repo_name,
        "--log-failed"
    ])
    if output is None:
        return None

    max_size = _get_max_log_size()
    if len(output) > max_size:
        output = _truncate_logs(output, max_size)

    return output


def format_failed_jobs(jobs: list[dict]) -> str:
    """Format failed jobs summary."""
    failed = [j for j in jobs if j.get("conclusion") == "failure"]
    if not failed:
        return "No failed jobs found."

    lines = []
    for job in failed:
        name = job.get("name", "Unknown")
        steps = job.get("steps", [])
        failed_steps = [s for s in steps if s.get("conclusion") == "failure"]

        lines.append(f"### Job: {name}")
        if failed_steps:
            lines.append("Failed steps:")
            for step in failed_steps:
                step_name = step.get("name", "Unknown")
                lines.append(f"  - {step_name}")
        lines.append("")

    return "\n".join(lines)


def validate_and_load_config() -> Config:
    """Validate required environment variables and return configuration.

    Raises:
        SystemExit: If required environment variables are missing.
    """
    try:
        api_key = _get_required_env("LLM_API_KEY")
        github_token = _get_required_env("GITHUB_TOKEN")
        run_id = _get_required_env("RUN_ID")
        repo_name = _get_required_env("REPO_NAME")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    return Config(
        api_key=api_key,
        github_token=github_token,
        model=os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929"),
        base_url=os.getenv("LLM_BASE_URL"),
        run_id=run_id,
        repo_name=repo_name,
    )


def fetch_workflow_data(run_id: str, repo_name: str) -> WorkflowData:
    """Fetch workflow run data from GitHub.

    Raises:
        SystemExit: If workflow data cannot be fetched.
    """
    run_info = get_workflow_run_info(run_id, repo_name)
    if run_info is None:
        logger.error("Failed to fetch workflow run info (API error)")
        sys.exit(1)

    workflow_name = run_info.get("name", "Unknown")
    branch = run_info.get("headBranch", "unknown")
    commit_sha = run_info.get("headSha", "unknown")
    triggered_by = run_info.get("event", "unknown")
    jobs = run_info.get("jobs", [])

    logger.info(f"Workflow: {workflow_name}")
    logger.info(f"Branch: {branch}")
    logger.info(f"Commit: {commit_sha[:8] if commit_sha != 'unknown' else commit_sha}")

    failed_jobs_summary = format_failed_jobs(jobs)
    logs = get_failed_job_logs(run_id, repo_name)

    if logs is None:
        logger.warning("Failed to fetch logs (API error)")
        logs = "Log fetch failed. Use `gh run view --log-failed` to investigate."
    elif not logs:
        logger.warning("No failed job logs found")
        logs = "No logs available. Use `gh run view --log-failed` to investigate."

    return WorkflowData(
        name=workflow_name,
        branch=branch,
        commit_sha=commit_sha,
        triggered_by=triggered_by,
        jobs=jobs,
        failed_jobs_summary=failed_jobs_summary,
        logs=logs,
    )


def create_agent(config: Config) -> Agent:
    """Create and configure the debug agent."""
    _require_openhands_runtime()

    llm_config = {
        "model": config.model,
        "api_key": config.api_key,
        "usage_id": "ci_debug_agent",
        "drop_params": True,
    }
    if config.base_url:
        llm_config["base_url"] = config.base_url

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


def execute_debug_agent(
    config: Config, workflow_data: WorkflowData
) -> Conversation:
    """Build prompt, create agent, and run debug analysis."""
    prompt = format_prompt(
        run_id=config.run_id,
        repo_name=config.repo_name,
        workflow_name=workflow_data.name,
        branch=workflow_data.branch,
        commit_sha=workflow_data.commit_sha,
        triggered_by=workflow_data.triggered_by,
        failed_jobs=workflow_data.failed_jobs_summary,
        logs=workflow_data.logs,
    )

    agent = create_agent(config)

    secrets = {
        "LLM_API_KEY": config.api_key,
        "GITHUB_TOKEN": config.github_token,
    }

    cwd = os.getcwd()
    conversation = Conversation(
        agent=agent,
        workspace=cwd,
        secrets=secrets,
    )

    logger.info("Starting CI failure analysis...")
    conversation.send_message(prompt)
    conversation.run()

    return conversation


def log_cost_summary(conversation: Conversation) -> None:
    """Print cost information for CI output."""
    metrics = conversation.conversation_stats.get_combined_metrics()
    print("\n=== CI Debug Cost Summary ===")
    print(f"Total Cost: ${metrics.accumulated_cost:.6f}")
    if metrics.accumulated_token_usage:
        token_usage = metrics.accumulated_token_usage
        print(f"Prompt Tokens: {token_usage.prompt_tokens}")
        print(f"Completion Tokens: {token_usage.completion_tokens}")


def _is_debug_workflow_by_env() -> bool:
    """Check if running inside a debug workflow via env var marker.

    This is the most robust check - if OH_DEBUG_WORKFLOW=true is set in the
    action.yml, we know definitively this is a debug workflow run.
    """
    return os.getenv("OH_DEBUG_WORKFLOW", "").lower() == "true"


def _is_debug_workflow_by_name(workflow_name: str) -> bool:
    """Check if workflow name matches known debug workflow patterns.

    This is a fallback check using name patterns. Less robust than env var
    but catches cases where the debug workflow has a custom name.
    """
    debug_workflow_names = [
        "debug ci failure",
        "debug-ci-failure",
        "ci debug",
        "debug ci",
    ]
    return workflow_name.lower().strip() in debug_workflow_names


def main():
    """Run the CI debug agent."""
    logger.info("Starting CI debug process...")

    # Primary recursion guard: check env var marker (most robust)
    # If this script is running inside a debug workflow action, OH_DEBUG_WORKFLOW=true
    # will be set by action.yml, regardless of what the workflow is named.
    if _is_debug_workflow_by_env():
        # This shouldn't happen in normal operation since the workflow YAML
        # should also filter out debug workflows. But if we somehow get here
        # (e.g., user misconfigured workflow), exit safely.
        logger.warning(
            "Detected OH_DEBUG_WORKFLOW=true - this appears to be a debug workflow "
            "trying to debug itself. Skipping to prevent recursion."
        )
        print("::warning::Skipped debugging debug workflow to prevent recursion")
        sys.exit(0)

    config = validate_and_load_config()
    logger.info(f"Debugging workflow run {config.run_id} in {config.repo_name}")

    try:
        workflow_data = fetch_workflow_data(config.run_id, config.repo_name)

        # Secondary recursion guard: check workflow name patterns
        # This catches cases where a workflow with a debug-related name failed
        if _is_debug_workflow_by_name(workflow_data.name):
            logger.warning(
                f"Skipping debug of workflow '{workflow_data.name}' to prevent "
                "recursive debugging. Debug workflows should not debug themselves."
            )
            print("::warning::Skipped debugging debug workflow to prevent recursion")
            sys.exit(0)

        conversation = execute_debug_agent(config, workflow_data)
        log_cost_summary(conversation)
        logger.info("CI debug analysis completed successfully")
    except GHCommandError as e:
        logger.error(str(e))
        # Output GitHub Actions annotation for visibility
        print(f"::error::CI debug failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"CI debug failed: {e}")
        # Output GitHub Actions annotation for visibility
        print(f"::error::CI debug failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
