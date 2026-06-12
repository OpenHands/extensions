# Agent Investigation Prompt

This document describes the structure of the prompt that `main.py` sends to the
OpenHands investigation conversation. The prompt is generated dynamically on each
trigger run. Understanding it helps with debugging, tuning, and extending the skill.

---

## When the Prompt is Sent

A new conversation is created (and this prompt sent) when — and only when — **all**
of the following are true:

1. No investigation conversation is currently active (`active_conversation` is `null`)
2. At least one trigger condition is met:
   - **Unknown logs:** one or more log events did not match any known pattern
   - **Spike:** at least one known pattern's current count exceeds
     `mean(last 3 runs) × SPIKE_MULTIPLIER`

A single conversation handles all triggers from that run together.

---

## Prompt Structure

The prompt is a Markdown document with four tasks:

### Task 1 — Categorize unknown logs

Shown only if `total_unknown > 0`. Contains:
- The total count of uncategorized logs detected
- A notice if the total exceeds `MAX_UNKNOWN_LOGS` (only a sample is shown)
- The sampled log messages, numbered, wrapped in `<unknown_logs>` tags
- The path to the state file where new patterns should be written
- Detailed instructions on the required pattern format

**Pattern writing format** the agent must follow:

```json
{
  "known_patterns": {
    "<new-uuid>": {
      "name": "...",
      "regex": "...",
      "run_history": [<count_from_this_window>],
      "last_seen": "<iso8601-utc>",
      "examples": [{"timestamp": "...", "message": "..."}]
    }
  }
}
```

The agent reads the current state file, merges in the new patterns, and writes it
back. It must preserve all existing patterns and the `last_poll_timestamp` and
`active_conversation` fields.

**Pattern quality guidance** embedded in the prompt:
- Avoid encoding timestamps, request IDs, memory addresses, PIDs, or UUIDs in regexes
- Prefer fewer, broader patterns over many narrow ones
- A good pattern matches the error *class*, not a single specific occurrence
- Use `.*` to skip variable parts between fixed anchors

### Task 2 — Investigate spiking patterns

Shown only if at least one pattern has a count spike. For each spiking pattern:
- Pattern name and regex
- Current count vs. recent baseline (formatted as `mean(last N runs)`)
- Up to `EXAMPLES_PER_PATTERN` example log messages (truncated to 300 chars each)

### Task 3 — Update and fix

Contains:
- List of repository paths with git host and remote identifier
- Instruction to `git pull` on each repo before investigating
- Decision gate:
  - **Code-level bugs:** create a PR only if highly confident
  - **Infrastructure/config/data issues:** describe findings, no PR

### Task 4 — Post Slack summary

Contains:
- The `SLACK_CHANNEL_ID` embedded in the script
- Required summary content: new categories, spike diagnoses, PRs or suggestions
- The `chat.postMessage` curl template
- Instruction to skip posting if no findings (no unknown logs, no spikes)

---

## Token Budget Considerations

The prompt size is bounded by these configurable limits:

| Parameter | Default | Controls |
|---|---|---|
| `MAX_UNKNOWN_LOGS` | 100 | Max uncategorized log messages included in the prompt |
| `EXAMPLES_PER_PATTERN` | 5 | Max example logs shown per spiking pattern |
| `MAX_LOG_MESSAGE_CHARS` | 500 | Max chars per log message in the prompt |

At defaults with 100 unknown logs and 5 spiking patterns with 5 examples each,
the prompt is roughly 60–80 KB — comfortably within context limits for modern LLMs.

If a query is returning a very high volume of uncategorized logs every run,
reduce `MAX_UNKNOWN_LOGS` during setup, or tighten the Datadog query filter
to reduce noise.

---

## Investigation Conversation Workspace

The agent conversation is started with `working_dir` set to the first configured
repository path (or a dedicated `dd-monitor-investigations/` directory if no
repos are configured). All user secrets and MCP configuration are forwarded so
the agent has the same tool access as any other OpenHands conversation.

The agent uses `terminal` and `file_editor` tools to:
- Navigate repository code (`cd`, `grep`, `git log`)
- Pull latest changes (`git pull`)
- Read and write the state file (to add new patterns)
- Create branches and PRs using the appropriate git host CLI

---

## Example Prompt Excerpt

```markdown
# Datadog Error Monitor — Investigation Request

## Context
- **Datadog query:** `service:(api OR worker) status:error`
- **Time window:** 2024-03-15T14:00:00Z → 2024-03-15T14:14:50Z
- **State file path:** `/home/user/.openhands/workspaces/automation-state/dd_monitor_abc123.json`

## Your Tasks

### Task 1 — Categorize unknown logs
There are **47 uncategorized log events** in this window.

For each distinct error type you identify, add a new entry to `known_patterns`
in the state file: `/home/user/.openhands/workspaces/automation-state/dd_monitor_abc123.json`

...

<unknown_logs>
[1] Connection refused to postgres://db.internal:5432/production at pool.js:88
[2] ETIMEDOUT: request to https://payments.stripe.com/v1/charges timed out after 30000ms
...
[47] Cannot read property 'id' of undefined at UserController.update (user.js:214)
</unknown_logs>

### Task 2 — Investigate spiking patterns

#### Pattern: `Redis connection timeout in CacheService`
- Current count: **47**
- Recent baseline: 1.3 (last 3 runs: [2, 1, 1])
- Regex: `(?:redis|Redis).*(?:timeout|connection refused).*CacheService`
...
```
