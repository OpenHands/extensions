#!/usr/bin/env python3
"""
Jenkins CI Debug Agent

This script runs an OpenHands agent to debug Jenkins CI/CD pipeline failures.
The agent fetches failed build logs, analyzes errors, and provides actionable fixes.

Environment Variables:
    LLM_API_KEY: API key for the LLM (required)
    LLM_MODEL: Language model to use (default: anthropic/claude-sonnet-4-5-20250929)
    LLM_BASE_URL: Optional base URL for LLM API
    JENKINS_URL: Jenkins server URL (required)
    JENKINS_USER: Jenkins username (required)
    JENKINS_API_TOKEN: Jenkins API token (required)
    JOB_NAME: Jenkins job name (required)
    BUILD_NUMBER: Build number to debug (optional, defaults to lastFailedBuild)

Usage:
    python agent_script.py --job "my-pipeline" --build 123
    python agent_script.py --job "my-pipeline" --last-failed
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from openhands.sdk import LLM, Agent, AgentContext, Conversation, get_logger
from openhands.sdk.context.skills import load_project_skills
from openhands.tools.preset.default import get_default_condenser, get_default_tools

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from prompt import format_prompt

logger = get_logger(__name__)

# Max characters to keep from logs. Configurable via MAX_LOG_SIZE env var.
# Default keeps ~50k chars which is roughly 12k tokens.
DEFAULT_MAX_LOG_SIZE = 50000


class JenkinsAPIError(Exception):
    """Raised when a Jenkins API request fails."""

    pass


@dataclass
class Config:
    """Configuration for the Jenkins debug agent."""

    api_key: str
    model: str
    base_url: str | None
    jenkins_url: str
    jenkins_user: str
    jenkins_token: str


@dataclass
class BuildData:
    """Data fetched from Jenkins about a build."""

    job_name: str
    build_number: str
    result: str
    duration: str
    timestamp: str
    stages: str
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


def _jenkins_api_request(
    url: str, jenkins_url: str, user: str, token: str
) -> dict | str | None:
    """Make a Jenkins API request.

    Returns:
        dict for JSON responses, str for text responses, None on failure.
    """
    if not url.startswith("http"):
        url = f"{jenkins_url.rstrip('/')}/{url.lstrip('/')}"

    credentials = base64.b64encode(f"{user}:{token}".encode()).decode()

    request = urllib.request.Request(url)
    request.add_header("Authorization", f"Basic {credentials}")
    request.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read().decode("utf-8", errors="replace")
            if "application/json" in content_type:
                return json.loads(data)
            return data
    except urllib.error.HTTPError as e:
        logger.warning(f"Jenkins API request failed: HTTP {e.code} {e.reason}")
        return None
    except urllib.error.URLError as e:
        logger.warning(f"Jenkins API request failed: {e.reason}")
        return None


def get_build_info(
    jenkins_url: str, user: str, token: str, job_name: str, build_number: str
) -> dict | None:
    """Fetch build information from Jenkins.

    Returns:
        dict on success, None on failure.
    """
    url = f"/job/{job_name}/{build_number}/api/json"
    result = _jenkins_api_request(url, jenkins_url, user, token)
    if result is None:
        return None
    return result if isinstance(result, dict) else None


# Default error patterns for log analysis. Configurable via ERROR_PATTERNS_FILE env var.
# Each pattern should be a valid regex. Patterns are checked in order (first match wins).
DEFAULT_ERROR_PATTERNS = [
    r"(?i)error[:\s]",
    r"(?i)failed[:\s]",
    r"(?i)exception[:\s]",
    r"(?i)traceback",
    r"(?i)fatal[:\s]",
    r"(?i)build failed",
    r"(?i)RejectedAccessException",
    r"(?i)CredentialsNotFoundException",
    r"(?i)timeout",
]


def _load_error_patterns() -> list[str]:
    """Load error patterns from file or use defaults.

    Configurable via ERROR_PATTERNS_FILE env var pointing to a JSON file
    containing a list of regex patterns. This allows customization for
    different languages/frameworks (Maven, Gradle, NPM, etc.).

    Example patterns file:
    [
        "(?i)BUILD FAILURE",        // Maven
        "(?i)FAILURE: Build failed", // Gradle
        "(?i)npm ERR!"              // NPM
    ]
    """
    patterns_file = os.getenv("ERROR_PATTERNS_FILE")
    if patterns_file:
        try:
            with open(patterns_file, "r") as f:
                patterns = json.load(f)
                if isinstance(patterns, list) and all(isinstance(p, str) for p in patterns):
                    logger.info(f"Loaded {len(patterns)} custom error patterns from {patterns_file}")
                    return patterns
                else:
                    logger.warning("Invalid patterns file format, using defaults")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load patterns file {patterns_file}: {e}, using defaults")

    return DEFAULT_ERROR_PATTERNS


def _find_error_context(logs: str, max_size: int, error_patterns: list[str] | None = None) -> str | None:
    """Extract context around error patterns in logs.

    Args:
        logs: The full log content
        max_size: Maximum characters to return
        error_patterns: Custom patterns to use (defaults to loaded patterns)
    """
    if error_patterns is None:
        error_patterns = _load_error_patterns()

    lines = logs.split("\n")

    error_indices = []
    for i, line in enumerate(lines):
        for pattern in error_patterns:
            if re.search(pattern, line):
                error_indices.append(i)
                break

    if error_indices:
        first_error = error_indices[0]
        total_lines = len(lines)
        avg_line_len = len(logs) // max(total_lines, 1)
        context_lines = max_size // max(avg_line_len, 50)

        before_context = int(context_lines * 0.2)
        after_context = context_lines - before_context

        start = max(0, first_error - before_context)
        end = min(total_lines, first_error + after_context)

        extracted_lines = lines[start:end]
        extracted = "\n".join(extracted_lines)

        if len(extracted) > max_size:
            extracted = extracted[:max_size]

        truncation_note = ""
        if start > 0 or end < total_lines:
            truncation_note = (
                f"\n[Context extracted around error at line {first_error + 1}. "
                f"Original log: {total_lines} lines]\n\n"
            )
        return truncation_note + extracted

    return None


def _truncate_logs(logs: str, max_size: int) -> str:
    """Truncate logs intelligently, preserving error context."""
    context_result = _find_error_context(logs, max_size)
    if context_result:
        return context_result

    first_chunk = int(max_size * 0.4)
    last_chunk = max_size - first_chunk
    truncated_chars = len(logs) - max_size
    return (
        logs[:first_chunk] +
        f"\n\n[... {truncated_chars:,} characters truncated ...]\n\n" +
        logs[-last_chunk:]
    )


def get_console_output(
    jenkins_url: str, user: str, token: str, job_name: str, build_number: str
) -> str | None:
    """Fetch console output from a Jenkins build.

    If logs exceed MAX_LOG_SIZE, uses context-aware truncation.

    Returns:
        Logs string on success, None on failure.
    """
    url = f"/job/{job_name}/{build_number}/consoleText"
    result = _jenkins_api_request(url, jenkins_url, user, token)
    if result is None:
        return None

    output = result if isinstance(result, str) else ""
    max_size = _get_max_log_size()
    if len(output) > max_size:
        output = _truncate_logs(output, max_size)

    return output


def get_pipeline_stages(
    jenkins_url: str, user: str, token: str, job_name: str, build_number: str
) -> str:
    """Fetch pipeline stage information using the Workflow API."""
    url = f"/job/{job_name}/{build_number}/wfapi/describe"
    result = _jenkins_api_request(url, jenkins_url, user, token)

    if not isinstance(result, dict) or "stages" not in result:
        return "Pipeline stage information not available (may not be a Pipeline job)."

    stages = result.get("stages", [])
    if not stages:
        return "No stages found."

    lines = []
    for stage in stages:
        name = stage.get("name", "Unknown")
        status = stage.get("status", "UNKNOWN")
        duration_ms = stage.get("durationMillis", 0)
        duration_s = duration_ms / 1000

        icon = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "⚠️"
        lines.append(f"{icon} **{name}**: {status} ({duration_s:.1f}s)")

    return "\n".join(lines)


def get_last_failed_build(
    jenkins_url: str, user: str, token: str, job_name: str
) -> str | None:
    """Get the last failed build number for a job."""
    url = f"/job/{job_name}/lastFailedBuild/api/json"
    result = _jenkins_api_request(url, jenkins_url, user, token)
    if isinstance(result, dict) and "number" in result:
        return str(result["number"])
    return None


def format_duration(duration_ms: int) -> str:
    """Format duration in milliseconds to human-readable string."""
    seconds = duration_ms // 1000
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    seconds = seconds % 60
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes}m {seconds}s"


def format_timestamp(timestamp_ms: int) -> str:
    """Format timestamp in milliseconds to human-readable string."""
    dt = datetime.fromtimestamp(timestamp_ms / 1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def validate_and_load_config() -> Config:
    """Validate required environment variables and return configuration.

    Raises:
        SystemExit: If required environment variables are missing.
    """
    try:
        api_key = _get_required_env("LLM_API_KEY")
        jenkins_url = _get_required_env("JENKINS_URL")
        jenkins_user = _get_required_env("JENKINS_USER")
        jenkins_token = _get_required_env("JENKINS_API_TOKEN")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    return Config(
        api_key=api_key,
        model=os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929"),
        base_url=os.getenv("LLM_BASE_URL"),
        jenkins_url=jenkins_url,
        jenkins_user=jenkins_user,
        jenkins_token=jenkins_token,
    )


def fetch_build_data(
    config: Config, job_name: str, build_number: str
) -> BuildData:
    """Fetch build data from Jenkins.

    Raises:
        SystemExit: If build data cannot be fetched.
    """
    build_info = get_build_info(
        config.jenkins_url, config.jenkins_user, config.jenkins_token,
        job_name, build_number
    )
    if build_info is None:
        logger.error("Failed to fetch build info (API error)")
        sys.exit(1)

    build_result = build_info.get("result", "UNKNOWN")
    duration = format_duration(build_info.get("duration", 0))
    timestamp = format_timestamp(build_info.get("timestamp", 0))

    logger.info(f"Build result: {build_result}")
    logger.info(f"Duration: {duration}")

    stages = get_pipeline_stages(
        config.jenkins_url, config.jenkins_user, config.jenkins_token,
        job_name, build_number
    )
    logs = get_console_output(
        config.jenkins_url, config.jenkins_user, config.jenkins_token,
        job_name, build_number
    )

    if logs is None:
        logger.warning("Failed to fetch console output (API error)")
        logs = "Console output fetch failed."
    elif not logs:
        logger.warning("No console output found")
        logs = "No console output available."

    return BuildData(
        job_name=job_name,
        build_number=build_number,
        result=build_result,
        duration=duration,
        timestamp=timestamp,
        stages=stages,
        logs=logs,
    )


def create_agent(config: Config) -> Agent:
    """Create and configure the debug agent."""
    llm_config = {
        "model": config.model,
        "api_key": config.api_key,
        "usage_id": "jenkins_debug_agent",
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


def execute_debug_agent(config: Config, build_data: BuildData) -> Conversation:
    """Build prompt, create agent, and run debug analysis."""
    prompt = format_prompt(
        jenkins_url=config.jenkins_url,
        job_name=build_data.job_name,
        build_number=build_data.build_number,
        build_result=build_data.result,
        duration=build_data.duration,
        timestamp=build_data.timestamp,
        stages=build_data.stages,
        logs=build_data.logs,
    )

    agent = create_agent(config)

    secrets = {
        "LLM_API_KEY": config.api_key,
        "JENKINS_API_TOKEN": config.jenkins_token,
    }

    cwd = os.getcwd()
    conversation = Conversation(
        agent=agent,
        workspace=cwd,
        secrets=secrets,
    )

    logger.info("Starting Jenkins build failure analysis...")
    conversation.send_message(prompt)
    conversation.run()

    return conversation


def log_cost_summary(conversation: Conversation) -> None:
    """Print cost information."""
    metrics = conversation.conversation_stats.get_combined_metrics()
    print("\n=== Jenkins Debug Cost Summary ===")
    print(f"Total Cost: ${metrics.accumulated_cost:.6f}")
    if metrics.accumulated_token_usage:
        token_usage = metrics.accumulated_token_usage
        print(f"Prompt Tokens: {token_usage.prompt_tokens}")
        print(f"Completion Tokens: {token_usage.completion_tokens}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Debug Jenkins CI failures")
    parser.add_argument("--job", required=True, help="Jenkins job name")
    parser.add_argument("--build", help="Build number to debug")
    parser.add_argument(
        "--last-failed", action="store_true", help="Debug the last failed build"
    )
    return parser.parse_args()


def resolve_build_number(config: Config, job_name: str, args: argparse.Namespace) -> str:
    """Resolve which build number to debug.

    Raises:
        SystemExit: If no build number can be determined.
    """
    if args.build:
        return args.build

    build_number = get_last_failed_build(
        config.jenkins_url, config.jenkins_user, config.jenkins_token, job_name
    )
    if not build_number:
        logger.error(f"No failed builds found for job '{job_name}'")
        sys.exit(1)
    return build_number


def main():
    """Run the Jenkins debug agent."""
    args = parse_args()
    logger.info("Starting Jenkins debug process...")

    config = validate_and_load_config()
    job_name = args.job
    build_number = resolve_build_number(config, job_name, args)

    logger.info(f"Debugging build {build_number} of job '{job_name}'")

    try:
        build_data = fetch_build_data(config, job_name, build_number)
        conversation = execute_debug_agent(config, build_data)
        log_cost_summary(conversation)
        logger.info("Jenkins debug analysis completed successfully")
    except JenkinsAPIError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Jenkins debug failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
