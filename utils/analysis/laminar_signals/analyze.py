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
LAMINAR_APP_URL = "https://www.lmnr.ai"
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
                "description": "Specific, actionable recommendations to fix the identified issues",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Short title for this recommendation"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of how to implement this fix"
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


def get_env_var(name: str) -> str:
    """Get a required environment variable or raise an error."""
    value = os.getenv(name)
    if not value:
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
    """Query Laminar SQL API to fetch signal events."""
    query = f"""
    SELECT id, trace_id, name, payload, timestamp 
    FROM signal_events 
    WHERE name = '{signal_name}' 
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
    """List all available signal names and their counts."""
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
    if project_id and trace_id:
        trace_url = f"{LAMINAR_APP_URL}/project/{project_id}/traces/{trace_id}"
    elif trace_id:
        # Fallback without project_id - user will need to be logged in
        trace_url = f"{LAMINAR_APP_URL}/traces/{trace_id}"
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
) -> str:
    """Build the analysis prompt using Jinja template."""
    template = Template(template_str)
    return template.render(
        signals=signals,
        num_signals=len(signals),
        signal_name=signal_name,
    )


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
                try:
                    return json.loads(message["content"])
                except json.JSONDecodeError:
                    pass
            
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
    signals = [parse_signal(s) for s in raw_signals]
    
    # Load prompt template
    template_str = load_prompt_template(args.signal, args.prompt_file)
    if args.prompt_file:
        template_source = f"custom ({args.prompt_file})"
    elif args.signal in BUILTIN_TEMPLATES:
        template_source = f"built-in ({BUILTIN_TEMPLATES[args.signal]})"
    else:
        template_source = "default (default.j2)"
    print(f"Using {template_source} prompt template", file=sys.stderr)
    
    # Build prompt and query LLM
    print("Building analysis prompt...", file=sys.stderr)
    prompt = build_analysis_prompt(signals, args.signal, template_str)
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
