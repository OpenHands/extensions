#!/usr/bin/env python3
"""
Laminar Signal Analysis Script

Downloads signal events from Laminar and uses an LLM to analyze patterns.
Supports customizable prompts via Jinja templates for different use cases.

Usage:
    python analyze_laminar_signals.py --signal "pr review suggestion and analysis"
    python analyze_laminar_signals.py --signal "my-signal" --prompt-file custom_prompt.j2
    python analyze_laminar_signals.py --signal "my-signal" --days 30

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
DEFAULT_LLM_BASE_URL = "https://llm-proxy.app.all-hands.dev"
DEFAULT_LLM_MODEL = "gemini-3-pro-preview"
DEFAULT_DAYS_LOOKBACK = 90


# Default prompt template for PR review signal analysis
# Can be overridden by providing a custom template file
DEFAULT_PROMPT_TEMPLATE = """
You are an expert at analyzing AI agent behavior patterns. Your task is to analyze a collection of signal data to identify trends and patterns.

## Context

The data below contains {{ num_signals }} signal events named "{{ signal_name }}".
Each signal has a timestamp and a payload with structured data.

## Signal Data

{% for signal in signals %}
### Signal {{ loop.index }} ({{ signal.timestamp }})

**Payload:**
```json
{{ signal.payload_json }}
```

---
{% endfor %}

## Your Task

Based on this data, provide a comprehensive analysis that addresses:

1. **Key Patterns**: What consistent patterns emerge from the data?

2. **Anomalies**: Are there any outliers or unusual events worth noting?

3. **Trends Over Time**: Do you notice any changes in behavior over time?

4. **Actionable Recommendations**: Based on the analysis, what improvements or actions would you recommend?

Please be specific and cite examples from the data where relevant.
"""

# Specialized prompt template for PR review signal analysis
PR_REVIEW_PROMPT_TEMPLATE = """
You are an expert at analyzing AI agent behavior patterns. Your task is to analyze a collection of PR review signal data to identify trends in what makes agent code reviews consistently good or consistently bad.

## Context

The data below contains {{ num_signals }} signal events from an AI PR review agent. Each signal has:
- **analysis**: A detailed explanation of what happened during the review
- **ai_suggestions**: Number of suggestions the AI made
- **ai_suggestions_reflected**: Number of AI suggestions that were implemented
- **human_suggestions**: Number of suggestions humans made  
- **human_suggestions_reflected**: Number of human suggestions that were implemented
- **total_suggestions_reflected**: Total suggestions implemented

## Signal Data

{% for signal in signals %}
### Signal {{ loop.index }} ({{ signal.timestamp }})

**Metrics:**
- AI suggestions: {{ signal.ai_suggestions }}
- AI suggestions reflected: {{ signal.ai_suggestions_reflected }}
- Human suggestions: {{ signal.human_suggestions }}
- Human suggestions reflected: {{ signal.human_suggestions_reflected }}

**Analysis:**
{{ signal.analysis }}

---
{% endfor %}

## Your Task

Based on this data, provide a comprehensive analysis that addresses:

1. **Consistently Good Behaviors**: What patterns emerge when the AI reviewer is effective? What types of suggestions get accepted? What review approaches lead to positive outcomes?

2. **Consistently Bad Behaviors**: What patterns emerge when the AI reviewer fails or is ineffective? What types of suggestions get rejected? What mistakes does the AI repeatedly make?

3. **Actionable Recommendations**: Based on the trends, what specific improvements should be made to the AI reviewer's behavior, prompts, or approach?

4. **Quantitative Summary**: Summarize the acceptance rates and any notable statistical patterns.

Please be specific and cite examples from the data where relevant.
"""

# Registry of built-in prompt templates for specific signal types
BUILTIN_TEMPLATES = {
    "pr review suggestion and analysis": PR_REVIEW_PROMPT_TEMPLATE,
}


def get_env_var(name: str) -> str:
    """Get a required environment variable or raise an error."""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


def query_laminar_signals(api_key: str, signal_name: str, days: int) -> list[dict]:
    """Query Laminar SQL API to fetch signal events."""
    query = f"""
    SELECT id, name, payload, timestamp 
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


def parse_signal(signal: dict) -> dict:
    """Parse signal and extract payload as both dict and formatted JSON."""
    payload_str = signal.get("payload", "{}")
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        payload = {}
    
    # Return signal data with both parsed payload fields and formatted JSON
    result = {
        "id": signal.get("id"),
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
    """Load the appropriate prompt template."""
    # If a custom prompt file is provided, use it
    if prompt_file:
        prompt_path = Path(prompt_file)
        if not prompt_path.exists():
            print(f"Error: Prompt file not found: {prompt_file}", file=sys.stderr)
            sys.exit(1)
        return prompt_path.read_text()
    
    # Check for built-in template for this signal type
    if signal_name in BUILTIN_TEMPLATES:
        return BUILTIN_TEMPLATES[signal_name]
    
    # Fall back to default generic template
    return DEFAULT_PROMPT_TEMPLATE


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


def get_llm_config() -> tuple[str, str, str]:
    """Get LLM configuration from environment variables.
    
    Returns:
        Tuple of (api_key, model, base_url)
    """
    api_key = get_env_var("LLM_API_KEY")
    model = os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)
    base_url = os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL)
    return api_key, model, base_url


def query_llm(api_key: str, prompt: str, model: str, base_url: str) -> str:
    """Query the LLM with the analysis prompt."""
    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    
    request_data = json.dumps({
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
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
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        print(f"Error querying LLM: HTTP {e.code}", file=sys.stderr)
        print(f"Response: {e.read().decode('utf-8')}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze Laminar signal events using an LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Analyze PR review signals with built-in template
    python analyze_laminar_signals.py --signal "pr review suggestion and analysis"
    
    # List available signals
    python analyze_laminar_signals.py --list-signals
    
    # Use a custom prompt template
    python analyze_laminar_signals.py --signal "my-signal" --prompt-file my_prompt.j2
    
    # Analyze last 30 days
    python analyze_laminar_signals.py --signal "my-signal" --days 30

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
    
    print("=" * 60)
    print("Laminar Signal Analysis")
    print("=" * 60)
    print()
    
    # Fetch signals from Laminar
    print(f"Signal: {args.signal}")
    print(f"Fetching signals from Laminar (last {args.days} days)...")
    raw_signals = query_laminar_signals(laminar_key, args.signal, args.days)
    print(f"Found {len(raw_signals)} signal events")
    print()
    
    if not raw_signals:
        print("No signals found. Exiting.")
        return
    
    # Parse signals
    signals = [parse_signal(s) for s in raw_signals]
    
    # Load prompt template
    template_str = load_prompt_template(args.signal, args.prompt_file)
    template_source = "built-in" if args.signal in BUILTIN_TEMPLATES and not args.prompt_file else "custom" if args.prompt_file else "default"
    print(f"Using {template_source} prompt template")
    
    # Build prompt and query LLM
    print("Building analysis prompt...")
    prompt = build_analysis_prompt(signals, args.signal, template_str)
    print(f"Prompt length: {len(prompt)} characters")
    print()
    
    print(f"Querying LLM ({llm_model}) for analysis...")
    print("This may take a minute...")
    print()
    
    analysis = query_llm(llm_key, prompt, llm_model, llm_base_url)
    
    # Output results
    output_text = f"""{'=' * 60}
LLM ANALYSIS RESULTS
{'=' * 60}

{analysis}

{'=' * 60}
"""
    
    if args.output:
        Path(args.output).write_text(output_text)
        print(f"Analysis written to: {args.output}")
    else:
        print(output_text)


if __name__ == "__main__":
    main()
