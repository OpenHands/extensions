#!/usr/bin/env python3
"""Generate release notes with an OpenHands agent.

This script collects structured release metadata from GitHub, then asks an
OpenHands agent to make editorial decisions about which changes matter, which
PRs belong together, and how to phrase the final release notes.

Environment Variables:
    LLM_API_KEY: API key for the LLM (required)
    LLM_MODEL: Language model to use
    LLM_BASE_URL: Optional base URL for custom LLM endpoints
    GITHUB_TOKEN: GitHub token for API access (required)
    TAG: The release tag to generate notes for (required)
    PREVIOUS_TAG: Override automatic detection of previous release (optional)
    INCLUDE_INTERNAL: Include internal/infrastructure changes (default: false)
    OUTPUT_FORMAT: Output format - 'release' or 'changelog' (default: release)
    REPO_NAME: Repository name in format owner/repo (required)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

from openhands.sdk import LLM, Agent, AgentContext, Conversation, get_logger
from openhands.sdk.context.skills import load_project_skills
from openhands.sdk.conversation import get_agent_final_response
from openhands.tools.preset.default import get_default_condenser, get_default_tools

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from generate_release_notes import Change, ReleaseNotes, generate_release_notes, set_github_output  # noqa: E402
from prompt import format_prompt  # noqa: E402
from validate_release_notes import append_reference_coverage_appendix  # noqa: E402

logger = get_logger(__name__)

CATEGORY_ORDER = ["breaking", "features", "fixes", "docs", "internal", "other"]


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


def _get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() == "true"


def validate_environment() -> dict[str, Any]:
    """Validate required environment variables and return configuration."""
    return {
        "model": os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929"),
        "base_url": os.getenv("LLM_BASE_URL", ""),
        "api_key": _get_required_env("LLM_API_KEY"),
        "github_token": _get_required_env("GITHUB_TOKEN"),
        "tag": _get_required_env("TAG"),
        "previous_tag": os.getenv("PREVIOUS_TAG") or None,
        "include_internal": _get_bool_env("INCLUDE_INTERNAL", False),
        "output_format": os.getenv("OUTPUT_FORMAT", "release"),
        "repo_name": _get_required_env("REPO_NAME"),
    }


def create_agent(config: dict[str, Any]) -> Agent:
    """Create and configure the release-notes agent."""
    llm_config: dict[str, Any] = {
        "model": config["model"],
        "api_key": config["api_key"],
        "usage_id": "release_notes_agent",
        "drop_params": True,
    }
    if config["base_url"]:
        llm_config["base_url"] = config["base_url"]

    llm = LLM(**llm_config)

    cwd = os.getcwd()
    project_skills = load_project_skills(cwd)
    logger.info(
        "Loaded %s project skills: %s",
        len(project_skills),
        [skill.name for skill in project_skills],
    )

    agent_context = AgentContext(
        load_public_skills=False,
        skills=project_skills,
    )

    return Agent(
        llm=llm,
        tools=get_default_tools(enable_browser=False),
        agent_context=agent_context,
        system_prompt_kwargs={"cli_mode": True},
        condenser=get_default_condenser(
            llm=llm.model_copy(update={"usage_id": "release_notes_condenser"})
        ),
    )


def _truncate(text: str, limit: int = 280) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _format_change_block(change: Change, repo_name: str) -> str:
    pr_ref = f"#{change.pr_number}" if change.pr_number else change.sha[:7]
    labels = ", ".join(change.pr_labels) if change.pr_labels else "none"
    url = change.url or (
        f"https://github.com/{repo_name}/pull/{change.pr_number}"
        if change.pr_number
        else f"https://github.com/{repo_name}/commit/{change.sha}"
    )
    body = _truncate(change.body, 400) or "No PR body provided"

    return "\n".join(
        [
            f"- Ref: {pr_ref}",
            f"  Title: {change.message}",
            f"  Author: @{change.author}" if change.author else "  Author: unknown",
            f"  Suggested category: {change.category}",
            f"  Labels: {labels}",
            f"  URL: {url}",
            f"  Body: {body}",
        ]
    )


def build_change_candidates(notes: ReleaseNotes) -> str:
    """Build the structured candidate change list for the agent prompt."""
    lines: list[str] = []
    for category in CATEGORY_ORDER:
        changes = notes.changes.get(category, [])
        if not changes:
            continue
        lines.append(f"\nSuggested {category}:" )
        for change in changes:
            lines.append(_format_change_block(change, notes.repo_name))
    return "\n".join(lines).strip()


def build_new_contributors(notes: ReleaseNotes) -> str:
    """Build the new-contributors section for the agent prompt."""
    if not notes.new_contributors:
        return "- None"

    lines = []
    for contributor in notes.new_contributors:
        pr_text = f" in #{contributor.first_pr}" if contributor.first_pr else ""
        lines.append(f"- @{contributor.username} made their first contribution{pr_text}")
    return "\n".join(lines)


def extract_markdown(text: str) -> str:
    """Normalize the agent response into plain markdown."""
    cleaned = text.strip()
    fence_match = re.fullmatch(r"```(?:markdown)?\s*\n?(.*?)\n?```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    return cleaned


def build_prompt(notes: ReleaseNotes, include_internal: bool, output_format: str) -> str:
    """Build the prompt sent to the release-notes agent."""
    return format_prompt(
        repo_name=notes.repo_name,
        tag=notes.tag,
        previous_tag=notes.previous_tag,
        date=notes.date,
        commit_count=notes.commit_count,
        include_internal=include_internal,
        output_format=output_format,
        full_changelog_url=(
            f"https://github.com/{notes.repo_name}/compare/"
            f"{notes.previous_tag}...{notes.tag}"
        ),
        change_candidates=build_change_candidates(notes),
        new_contributors=build_new_contributors(notes),
    )


def run_generation(
    agent: Agent,
    prompt: str,
    secrets: dict[str, str],
) -> tuple[Conversation, str]:
    """Run the agent and return the conversation plus generated markdown."""
    conversation = Conversation(
        agent=agent,
        workspace=os.getcwd(),
        secrets=secrets,
    )

    logger.info("Starting agent-based release note generation...")
    conversation.send_message(prompt)
    conversation.run()

    response = get_agent_final_response(conversation.state.events)
    if not response:
        raise RuntimeError("Agent did not return release notes")

    return conversation, extract_markdown(response)


def log_cost_summary(conversation: Conversation) -> None:
    """Print cost information for CI output."""
    metrics = conversation.conversation_stats.get_combined_metrics()
    print("\n=== Release Notes Cost Summary ===")
    print(f"Total Cost: ${metrics.accumulated_cost:.6f}")
    if metrics.accumulated_token_usage:
        token_usage = metrics.accumulated_token_usage
        print(f"Prompt Tokens: {token_usage.prompt_tokens}")
        print(f"Completion Tokens: {token_usage.completion_tokens}")
        if token_usage.cache_read_tokens > 0:
            print(f"Cache Read Tokens: {token_usage.cache_read_tokens}")
        if token_usage.cache_write_tokens > 0:
            print(f"Cache Write Tokens: {token_usage.cache_write_tokens}")


def main() -> None:
    """Generate release notes with an agent and write outputs for GitHub Actions."""
    config = validate_environment()

    logger.info("Generating release notes for %s", config["repo_name"])
    logger.info("Tag: %s", config["tag"])
    logger.info("Previous tag: %s", config["previous_tag"] or "auto-detect")
    logger.info("Include internal: %s", config["include_internal"])
    logger.info("Output format: %s", config["output_format"])
    logger.info("LLM model: %s", config["model"])

    notes = generate_release_notes(
        tag=config["tag"],
        previous_tag=config["previous_tag"],
        repo_name=config["repo_name"],
        token=config["github_token"],
        include_internal=config["include_internal"],
    )

    prompt = build_prompt(
        notes=notes,
        include_internal=config["include_internal"],
        output_format=config["output_format"],
    )

    agent = create_agent(config)
    conversation, markdown = run_generation(
        agent=agent,
        prompt=prompt,
        secrets={
            "LLM_API_KEY": config["api_key"],
            "GITHUB_TOKEN": config["github_token"],
        },
    )
    markdown = append_reference_coverage_appendix(
        markdown,
        notes,
        include_internal=config["include_internal"],
    )

    with open("release_notes.md", "w") as file:
        file.write(markdown)

    print("\n" + "=" * 60)
    print("Generated Release Notes:")
    print("=" * 60)
    print(markdown)
    print("=" * 60)

    set_github_output("release_notes", markdown)
    set_github_output("previous_tag", notes.previous_tag)
    set_github_output("commit_count", str(notes.commit_count))
    set_github_output("contributor_count", str(len(notes.contributors)))
    set_github_output("new_contributor_count", str(len(notes.new_contributors)))

    log_cost_summary(conversation)
    logger.info("Release notes generated successfully")


if __name__ == "__main__":
    main()
