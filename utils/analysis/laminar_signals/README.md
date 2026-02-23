# Laminar Signal Analysis

Analyze Laminar signal events using LLMs with customizable Jinja2 prompt templates.

## Directory Structure

```
laminar_signals/
├── analyze.py          # Main analysis script
├── README.md           # This file
└── templates/
    ├── default.j2      # Generic template for any signal type
    └── pr_review.j2    # Specialized template for PR review signals
```

## Prerequisites

- Python 3.9+
- `jinja2` package

```bash
pip install jinja2
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LMNR_PROJECT_API_KEY` | Yes | - | Laminar project API key |
| `LLM_API_KEY` | Yes | - | API key for the LLM |
| `LLM_MODEL` | No | `gemini-3-pro-preview` | Model to use |
| `LLM_BASE_URL` | No | `https://llm-proxy.app.all-hands.dev` | Base URL for LLM API |

## Usage

```bash
# List available signals
python analyze.py --list-signals

# Analyze PR review signals (uses built-in template)
python analyze.py --signal "pr review suggestion and analysis"

# Analyze with custom prompt template
python analyze.py --signal "my-signal" --prompt-file my_prompt.j2

# Analyze last 30 days and save to file
python analyze.py --signal "my-signal" --days 30 --output results.md
```

## How It Works

1. **Fetches Signals**: Queries the Laminar SQL API (`/v1/sql/query`) to retrieve signal events from the `signal_events` table.

2. **Parses Data**: Extracts payload fields from each signal for template access.

3. **Generates Prompt**: Uses a Jinja2 template to construct an analysis prompt. Templates are loaded from:
   - Custom file if `--prompt-file` is specified
   - Built-in template from `templates/` if one exists for the signal type
   - `templates/default.j2` as fallback

4. **LLM Analysis**: Sends the prompt to the configured LLM for analysis.

## Built-in Templates

| Template | Signal Name | Focus |
|----------|-------------|-------|
| `pr_review.j2` | `pr review suggestion and analysis` | AI PR reviewer effectiveness, suggestion acceptance rates, good/bad behavior patterns |
| `default.j2` | (any) | Generic analysis of patterns, anomalies, trends, and recommendations |

## Custom Prompt Templates

Create a Jinja2 template file (`.j2`) with access to these variables:

| Variable | Type | Description |
|----------|------|-------------|
| `signals` | `list[dict]` | List of parsed signal objects |
| `num_signals` | `int` | Number of signals |
| `signal_name` | `str` | Name of the signal being analyzed |

Each signal object contains:
- `id`: Signal ID
- `timestamp`: When the signal was created
- `payload`: Parsed payload as dict
- `payload_json`: Formatted JSON string of payload
- All payload fields are also available at the top level for convenience

### Example Custom Template

```jinja2
Analyze these {{ num_signals }} events for "{{ signal_name }}":

{% for signal in signals %}
## Event {{ loop.index }}
Timestamp: {{ signal.timestamp }}
Score: {{ signal.score }}  {# if payload has 'score' field #}
{% endfor %}

What patterns do you see?
```

## PR Review Signal Data Structure

The `pr_review.j2` template expects signals with these payload fields:

| Field | Description |
|-------|-------------|
| `analysis` | Detailed explanation of what happened during the review |
| `ai_suggestions` | Number of suggestions the AI made |
| `ai_suggestions_reflected` | Number of AI suggestions implemented |
| `human_suggestions` | Number of suggestions humans made |
| `human_suggestions_reflected` | Number of human suggestions implemented |
| `total_suggestions_reflected` | Total suggestions implemented |

## Example Output

```
============================================================
Laminar Signal Analysis
============================================================

Signal: pr review suggestion and analysis
Fetching signals from Laminar (last 90 days)...
Found 113 signal events

Using built-in (pr_review.j2) prompt template
Building analysis prompt...
Prompt length: 135197 characters

Querying LLM (gemini-3-pro-preview) for analysis...
This may take a minute...

============================================================
LLM ANALYSIS RESULTS
============================================================

[Detailed analysis of patterns and recommendations...]

============================================================
```

## Laminar SQL API Reference

The script uses Laminar's SQL API at `/v1/sql/query`. Key tables:

- `signal_events`: Contains signal events with payload data
- `spans`: Contains trace span data
- `traces`: Contains trace-level aggregates

See [Laminar SQL Editor documentation](https://docs.laminar.sh/platform/sql-editor) for more details.
