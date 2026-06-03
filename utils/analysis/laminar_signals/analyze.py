#!/usr/bin/env python3
"""
Laminar Signal Analysis Script

Downloads signal events from Laminar and uses an LLM to analyze patterns.
Supports customizable prompts via Jinja templates for different use cases.
Uses function calling to get structured output with trace IDs.

Usage:
    python analyze.py --signal "pr review suggestion and analysis"
    python analyze.py --signal "my-signal" --prompt-file custom_prompt.j2
    python analyze.py --signal "my-signal" --days 30 --format json

Environment Variables:
    LMNR_PROJECT_API_KEY: Laminar project API key (required)
    LLM_API_KEY: API key for the LLM (required)
    LLM_MODEL: Model to use (default: gemini-3-pro-preview)
    LLM_BASE_URL: Base URL for LLM API (default: https://llm-proxy.app.all-hands.dev)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

from jinja2 import Template


LAMINAR_API_URL = "https://api.lmnr.ai/v1/sql/query"
LAMINAR_APP_URL = "https://laminar.sh"
DEFAULT_LLM_BASE_URL = "https://llm-proxy.app.all-hands.dev"
DEFAULT_LLM_MODEL = "gemini-3-pro-preview"
DEFAULT_DAYS_LOOKBACK = 90

# Directory containing this script
SCRIPT_DIR = Path(__file__).parent
TEMPLATES_DIR = SCRIPT_DIR / "templates"

# Mapping of signal names to their template files
BUILTIN_TEMPLATES = {
    "pr review suggestion and analysis": "pr_review.j2",
}


def load_skill_content(skill_dir: str) -> str:
    """Load skill/plugin content from a directory.
    
    Looks for SKILL.md files in the directory and any subdirectories.
    For plugins, also looks in skills/ subdirectory and scripts/prompt.py.
    
    Args:
        skill_dir: Path to skill or plugin directory
        
    Returns:
        Combined content of all skill files found
    """
    skill_path = Path(skill_dir)
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill directory not found: {skill_dir}")
    
    content_parts = []
    
    # Load main SKILL.md if present
    main_skill = skill_path / "SKILL.md"
    if main_skill.exists():
        content_parts.append(f"## Skill: {skill_path.name}\n\n{main_skill.read_text()}")
    
    # For plugins, check for prompt.py
    prompt_py = skill_path / "scripts" / "prompt.py"
    if prompt_py.exists():
        content_parts.append(f"## Prompt Template ({prompt_py.name})\n\n```python\n{prompt_py.read_text()}\n```")
    
    # Check for nested skills (common in plugins)
    skills_subdir = skill_path / "skills"
    if skills_subdir.exists():
        for nested_skill_dir in skills_subdir.iterdir():
            if nested_skill_dir.is_dir():
                nested_skill_md = nested_skill_dir / "SKILL.md"
                if nested_skill_md.exists():
                    content_parts.append(
                        f"## Nested Skill: {nested_skill_dir.name}\n\n{nested_skill_md.read_text()}"
                    )
    
    if not content_parts:
        raise FileNotFoundError(f"No SKILL.md or prompt.py found in: {skill_dir}")
    
    return "\n\n---\n\n".join(content_parts)

# JSON Schema for the analysis function call output
ANALYSIS_FUNCTION = {
    "name": "report_analysis",
    "description": "Report the analysis of signal events, focusing on issues and areas for improvement",
    "parameters": {
        "type": "object",
        "properties": {
            "issues": {
                "type": "array",
                "description": "List of issues, problems, and areas needing improvement (THIS IS THE PRIMARY FOCUS)",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Short title for this issue"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of the issue, why it's problematic, and its impact"
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                            "description": "How severe/impactful this issue is"
                        },
                        "frequency": {
                            "type": "string",
                            "description": "How often this issue occurs (e.g., '15% of traces', 'frequent', 'occasional')"
                        },
                        "trace_urls": {
                            "type": "array",
                            "description": "Up to 5 representative trace URLs demonstrating this issue",
                            "items": {"type": "string"},
                            "maxItems": 5
                        }
                    },
                    "required": ["title", "description", "severity", "trace_urls"]
                }
            },
            "recommendations": {
                "type": "array",
                "description": "Specific, actionable recommendations with CONCRETE implementation details (e.g., exact prompt changes, code snippets)",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Short title for this recommendation"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description with SPECIFIC implementation. Include exact prompt text changes, code modifications, or configuration updates. Use 'Change X to Y' format where possible."
                        },
                        "prompt_changes": {
                            "type": "array",
                            "description": "Specific prompt/instruction changes. Each item should have 'before' (current text) and 'after' (proposed text)",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "section": {"type": "string", "description": "Which section of the prompt to modify"},
                                    "before": {"type": "string", "description": "Current text (or 'N/A' if adding new)"},
                                    "after": {"type": "string", "description": "Proposed new text"}
                                },
                                "required": ["section", "after"]
                            }
                        },
                        "addresses": {
                            "type": "array",
                            "description": "Which issues this recommendation fixes",
                            "items": {"type": "string"}
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "description": "Priority for implementing this recommendation"
                        }
                    },
                    "required": ["title", "description", "addresses", "priority"]
                }
            },
            "strengths": {
                "type": "array",
                "description": "Brief list of things working well (keep this short, focus is on improvements)",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Short title"
                        },
                        "description": {
                            "type": "string",
                            "description": "Brief description of what's working well"
                        }
                    },
                    "required": ["title", "description"]
                }
            },
            "metrics": {
                "type": "object",
                "description": "Quantitative metrics from the analysis",
                "properties": {
                    "total_signals": {
                        "type": "integer",
                        "description": "Total number of signals analyzed"
                    },
                    "issue_rate": {
                        "type": "string",
                        "description": "Percentage of signals showing issues"
                    },
                    "key_statistics": {
                        "type": "array",
                        "description": "Other relevant statistics",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "value": {"type": "string"}
                            },
                            "required": ["name", "value"]
                        }
                    }
                },
                "required": ["total_signals"]
            },
            "summary": {
                "type": "string",
                "description": "Executive summary focusing on the most critical improvements needed"
            }
        },
        "required": ["issues", "recommendations", "metrics", "summary"]
    }
}


def get_env_var(name: str, required: bool = True) -> str | None:
    """Get an environment variable.
    
    Args:
        name: Environment variable name
        required: If True, raise error if not set. If False, return None.
    """
    value = os.getenv(name)
    if not value and required:
        raise ValueError(f"{name} environment variable is required")
    return value


def get_llm_config() -> tuple[str, str, str]:
    """Get LLM configuration from environment variables.
    
    Returns:
        Tuple of (api_key, model, base_url)
    """
    api_key = get_env_var("LLM_API_KEY")
    model = os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)
    base_url = os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL)
    return api_key, model, base_url


def query_laminar_signals(api_key: str, signal_name: str, days: int) -> list[dict]:
    """Query Laminar SQL API to fetch signal events.
    
    Note: days is validated as int by argparse, so no SQL injection risk there.
    """
    # Escape single quotes to prevent SQL injection
    escaped_signal = signal_name.replace("'", "''")
    query = f"""
    SELECT id, trace_id, name, payload, timestamp 
    FROM signal_events 
    WHERE name = '{escaped_signal}' 
    AND timestamp > now() - INTERVAL {days} DAY 
    ORDER BY timestamp DESC
    """
    
    request_data = json.dumps({"query": query}).encode("utf-8")
    request = urllib.request.Request(
        LAMINAR_API_URL,
        data=request_data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("data", [])
    except urllib.error.HTTPError as e:
        print(f"Error querying Laminar API: HTTP {e.code}", file=sys.stderr)
        print(f"Response: {e.read().decode('utf-8')}", file=sys.stderr)
        sys.exit(1)


def list_available_signals(api_key: str, days: int) -> list[dict]:
    """List all available signal names and their counts.
    
    Note: days is validated as int by argparse, so no SQL injection risk.
    """
    query = f"""
    SELECT name, COUNT(*) as count 
    FROM signal_events 
    WHERE timestamp > now() - INTERVAL {days} DAY 
    GROUP BY name 
    ORDER BY count DESC
    """
    
    request_data = json.dumps({"query": query}).encode("utf-8")
    request = urllib.request.Request(
        LAMINAR_API_URL,
        data=request_data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("data", [])
    except urllib.error.HTTPError as e:
        print(f"Error querying Laminar API: HTTP {e.code}", file=sys.stderr)
        return []


def parse_signal(signal: dict, project_id: str | None = None) -> dict:
    """Parse signal and extract payload as both dict and formatted JSON."""
    payload_str = signal.get("payload", "{}")
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        payload = {}
    
    signal_id = signal.get("id")
    trace_id = signal.get("trace_id")
    
    # Construct the Laminar trace URL
    # Format: https://laminar.sh/project/{project_id}/traces?traceId={trace_id}
    if project_id and trace_id:
        trace_url = f"{LAMINAR_APP_URL}/project/{project_id}/traces?traceId={trace_id}"
    else:
        trace_url = None
    
    # Return signal data with both parsed payload fields and formatted JSON
    result = {
        "id": signal_id,
        "trace_id": trace_id,
        "trace_url": trace_url,
        "timestamp": signal.get("timestamp"),
        "payload": payload,
        "payload_json": json.dumps(payload, indent=2),
    }
    
    # Also flatten payload fields to top level for easy template access
    for key, value in payload.items():
        if key not in result:
            result[key] = value
    
    return result


def load_prompt_template(
    signal_name: str,
    prompt_file: str | None = None,
) -> str:
    """Load the appropriate prompt template.
    
    Priority:
    1. Custom prompt file if provided
    2. Built-in template for the signal type
    3. Default template
    """
    # If a custom prompt file is provided, use it
    if prompt_file:
        prompt_path = Path(prompt_file)
        if not prompt_path.exists():
            print(f"Error: Prompt file not found: {prompt_file}", file=sys.stderr)
            sys.exit(1)
        return prompt_path.read_text()
    
    # Check for built-in template for this signal type
    if signal_name in BUILTIN_TEMPLATES:
        template_file = TEMPLATES_DIR / BUILTIN_TEMPLATES[signal_name]
        if template_file.exists():
            return template_file.read_text()
    
    # Fall back to default template
    default_template = TEMPLATES_DIR / "default.j2"
    if default_template.exists():
        return default_template.read_text()
    
    # Fallback if templates directory doesn't exist
    raise FileNotFoundError(
        f"No template found. Expected templates in: {TEMPLATES_DIR}"
    )


def build_analysis_prompt(
    signals: list[dict],
    signal_name: str,
    template_str: str,
    skill_content: str | None = None,
) -> str:
    """Build the analysis prompt using Jinja template."""
    template = Template(template_str)
    prompt = template.render(
        signals=signals,
        num_signals=len(signals),
        signal_name=signal_name,
    )
    
    # Append skill content if provided
    if skill_content:
        prompt += f"""

---

## Current Agent Skill/Prompt Configuration

The following is the current skill/prompt configuration that the agent uses. 
Your recommendations MUST be grounded in this configuration with SPECIFIC, ACTIONABLE changes.

{skill_content}

---

## CRITICAL REQUIREMENTS FOR RECOMMENDATIONS

Your recommendations MUST include SPECIFIC, ACTIONABLE prompt changes:

1. **Quote the exact text** from the skill/prompt that needs to change
2. **Provide the replacement text** - not vague suggestions, but actual wording
3. **Specify the section** where the change should be made
4. **Use the prompt_changes field** to provide before/after diffs

❌ BAD (vague): "Update the prompt to be more strict about blocking PRs"
✅ GOOD (specific): 
   - Section: VERDICT
   - Before: "❌ Needs rework: Fundamental design issues must be addressed first"
   - After: "❌ Needs rework: BLOCK the PR if any of these are found: 1. Security vulnerabilities 2. Race conditions 3. Missing tests for new behavior. Do NOT approve with suggestions for these categories."

❌ BAD: "Add instructions about deduplication"
✅ GOOD:
   - Section: CRITICAL REVIEW OUTPUT FORMAT (new subsection)
   - After: "**NOISE CONTROL**: If the same issue appears in multiple locations, post ONE comment on the first occurrence that summarizes the pattern (e.g., 'This None-check issue appears on lines X, Y, Z') rather than commenting on each line."

Be as specific as possible. The goal is for someone to copy-paste your suggested changes directly into the skill file.
"""
    
    return prompt


def query_llm(api_key: str, prompt: str, model: str, base_url: str) -> dict:
    """Query the LLM with the analysis prompt using function calling.
    
    Returns:
        Parsed JSON object from the function call response.
    """
    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    
    request_data = json.dumps({
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": ANALYSIS_FUNCTION,
            }
        ],
        "tool_choice": {
            "type": "function",
            "function": {"name": "report_analysis"}
        },
        "max_tokens": 8192,
        "temperature": 0.7,
    }).encode("utf-8")
    
    request = urllib.request.Request(
        url,
        data=request_data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))
            
            # Extract the function call arguments
            message = result["choices"][0]["message"]
            if "tool_calls" in message and message["tool_calls"]:
                tool_call = message["tool_calls"][0]
                if tool_call["type"] == "function":
                    return json.loads(tool_call["function"]["arguments"])
            
            # Fallback: try to parse content as JSON if no tool call
            if message.get("content"):
                content = message["content"]
                # Try to extract JSON from markdown code blocks
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    if end > start:
                        content = content[start:end].strip()
                elif "```" in content:
                    start = content.find("```") + 3
                    end = content.find("```", start)
                    if end > start:
                        content = content[start:end].strip()
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse LLM response as JSON", file=sys.stderr)
                    print(f"Response content: {message['content'][:500]}...", file=sys.stderr)
            
            raise ValueError("No function call response received from LLM")
            
    except urllib.error.HTTPError as e:
        print(f"Error querying LLM: HTTP {e.code}", file=sys.stderr)
        print(f"Response: {e.read().decode('utf-8')}", file=sys.stderr)
        sys.exit(1)


def format_analysis_as_markdown(analysis: dict, signal_name: str) -> str:
    """Convert the structured analysis output to markdown format."""
    lines = [
        "# Agent Improvement Report",
        "",
        f"**Signal:** `{signal_name}`",
        "",
    ]
    
    # Executive Summary
    if analysis.get("summary"):
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(analysis["summary"])
        lines.append("")
    
    # Issues (Primary Focus)
    lines.append("## Issues Requiring Attention")
    lines.append("")
    for i, issue in enumerate(analysis.get("issues", []), 1):
        severity = issue.get("severity", "medium").upper()
        lines.append(f"### {i}. [{severity}] {issue['title']}")
        lines.append("")
        lines.append(issue["description"])
        lines.append("")
        if issue.get("frequency"):
            lines.append(f"**Frequency:** {issue['frequency']}")
            lines.append("")
        if issue.get("trace_urls"):
            lines.append("**Example traces:**")
            for url in issue["trace_urls"]:
                lines.append(f"- {url}")
            lines.append("")
    
    # Recommendations
    lines.append("## Recommended Fixes")
    lines.append("")
    for i, rec in enumerate(analysis.get("recommendations", []), 1):
        priority = rec.get("priority", "medium").upper()
        lines.append(f"### {i}. [{priority} PRIORITY] {rec['title']}")
        lines.append("")
        lines.append(rec["description"])
        lines.append("")
        
        # Display specific prompt changes if provided
        if rec.get("prompt_changes"):
            lines.append("**Suggested Prompt Changes:**")
            lines.append("")
            for change in rec["prompt_changes"]:
                section = change.get("section", "Unknown section")
                before = change.get("before", "N/A")
                after = change.get("after", "")
                lines.append(f"📍 **Section:** {section}")
                lines.append("")
                if before and before != "N/A":
                    lines.append("```diff")
                    lines.append(f"- {before}")
                    lines.append(f"+ {after}")
                    lines.append("```")
                else:
                    lines.append("```")
                    lines.append(f"+ {after}")
                    lines.append("```")
                lines.append("")
        
        if rec.get("addresses"):
            lines.append(f"*Fixes: {', '.join(rec['addresses'])}*")
            lines.append("")
    
    # Metrics
    metrics = analysis.get("metrics", {})
    lines.append("## Metrics")
    lines.append("")
    lines.append(f"**Total signals analyzed:** {metrics.get('total_signals', 'N/A')}")
    if metrics.get("issue_rate"):
        lines.append(f"**Issue rate:** {metrics['issue_rate']}")
    lines.append("")
    
    if metrics.get("key_statistics"):
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for stat in metrics["key_statistics"]:
            lines.append(f"| {stat['name']} | {stat['value']} |")
        lines.append("")
    
    # Strengths (Brief)
    if analysis.get("strengths"):
        lines.append("## What's Working Well")
        lines.append("")
        for strength in analysis["strengths"]:
            lines.append(f"- **{strength['title']}**: {strength['description']}")
        lines.append("")
    
    return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze Laminar signal events using an LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Analyze PR review signals with built-in template
    python analyze.py --signal "pr review suggestion and analysis"
    
    # Analyze with skill context for grounded recommendations
    python analyze.py --signal "pr review suggestion and analysis" \\
        --skill-dir ../../../plugins/pr-review
    
    # List available signals
    python analyze.py --list-signals
    
    # Use a custom prompt template
    python analyze.py --signal "my-signal" --prompt-file my_prompt.j2
    
    # Analyze last 30 days with JSON output
    python analyze.py --signal "my-signal" --days 30 --format json

Environment Variables:
    LMNR_PROJECT_API_KEY  Laminar project API key (required)
    LLM_API_KEY           API key for the LLM (required)
    LLM_MODEL             Model to use (default: gemini-3-pro-preview)
    LLM_BASE_URL          Base URL for LLM API (default: https://llm-proxy.app.all-hands.dev)
        """,
    )
    parser.add_argument(
        "--signal",
        help="Name of the signal to analyze",
    )
    parser.add_argument(
        "--list-signals",
        action="store_true",
        help="List available signal names and exit",
    )
    parser.add_argument(
        "--prompt-file",
        help="Path to custom Jinja2 prompt template file",
    )
    parser.add_argument(
        "--skill-dir",
        help="Path to skill or plugin directory to ground recommendations in current prompts",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS_LOOKBACK,
        help=f"Number of days to look back (default: {DEFAULT_DAYS_LOOKBACK})",
    )
    parser.add_argument(
        "--format",
        choices=["md", "json"],
        default="md",
        help="Output format: 'md' for markdown (default), 'json' for raw JSON",
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: stdout)",
    )
    args = parser.parse_args()
    
    # Get API keys and config
    laminar_key = get_env_var("LMNR_PROJECT_API_KEY")
    laminar_project_id = get_env_var("LMNR_PROJECT_ID", required=False)
    llm_key, llm_model, llm_base_url = get_llm_config()
    
    # Handle --list-signals
    if args.list_signals:
        print(f"Available signals (last {args.days} days):")
        print()
        signals = list_available_signals(laminar_key, args.days)
        if not signals:
            print("  No signals found")
        else:
            for s in signals:
                builtin = " [has built-in template]" if s["name"] in BUILTIN_TEMPLATES else ""
                print(f"  {s['name']}: {s['count']} events{builtin}")
        return
    
    # Require --signal if not listing
    if not args.signal:
        parser.error("--signal is required (or use --list-signals)")
    
    print("=" * 60, file=sys.stderr)
    print("Laminar Signal Analysis", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(file=sys.stderr)
    
    # Fetch signals from Laminar
    print(f"Signal: {args.signal}", file=sys.stderr)
    print(f"Fetching signals from Laminar (last {args.days} days)...", file=sys.stderr)
    raw_signals = query_laminar_signals(laminar_key, args.signal, args.days)
    print(f"Found {len(raw_signals)} signal events", file=sys.stderr)
    print(file=sys.stderr)
    
    if not raw_signals:
        print("No signals found. Exiting.", file=sys.stderr)
        return
    
    # Parse signals
    signals = [parse_signal(s, laminar_project_id) for s in raw_signals]
    
    # Warn if no project ID (trace URLs won't be generated)
    if not laminar_project_id:
        print("Warning: LMNR_PROJECT_ID not set, trace URLs will not be generated", file=sys.stderr)
        print("Set LMNR_PROJECT_ID to enable clickable trace links", file=sys.stderr)
        print(file=sys.stderr)
    
    # Load prompt template
    template_str = load_prompt_template(args.signal, args.prompt_file)
    if args.prompt_file:
        template_source = f"custom ({args.prompt_file})"
    elif args.signal in BUILTIN_TEMPLATES:
        template_source = f"built-in ({BUILTIN_TEMPLATES[args.signal]})"
    else:
        template_source = "default (default.j2)"
    print(f"Using {template_source} prompt template", file=sys.stderr)
    
    # Load skill content if provided
    skill_content = None
    if args.skill_dir:
        print(f"Loading skill content from: {args.skill_dir}", file=sys.stderr)
        try:
            skill_content = load_skill_content(args.skill_dir)
            print(f"Loaded {len(skill_content)} characters of skill content", file=sys.stderr)
        except FileNotFoundError as e:
            print(f"Warning: {e}", file=sys.stderr)
    
    # Build prompt and query LLM
    print("Building analysis prompt...", file=sys.stderr)
    prompt = build_analysis_prompt(signals, args.signal, template_str, skill_content)
    print(f"Prompt length: {len(prompt)} characters", file=sys.stderr)
    print(file=sys.stderr)
    
    print(f"Querying LLM ({llm_model}) for analysis...", file=sys.stderr)
    print("This may take a minute...", file=sys.stderr)
    print(file=sys.stderr)
    
    analysis = query_llm(llm_key, prompt, llm_model, llm_base_url)
    
    # Format output based on requested format
    if args.format == "json":
        output_text = json.dumps(analysis, indent=2)
    else:
        output_text = format_analysis_as_markdown(analysis, args.signal)
    
    # Write output
    if args.output:
        Path(args.output).write_text(output_text)
        print(f"Analysis written to: {args.output}", file=sys.stderr)
    else:
        print(output_text)


if __name__ == "__main__":
    main()
