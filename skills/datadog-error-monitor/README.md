# datadog-error-monitor

An OpenHands skill that creates an automated Datadog error monitoring loop.

## What it does

A cron automation runs every 15 minutes, querying Datadog logs with a
pre-configured filter. It maintains a library of known error patterns (regex-based)
and their historical hit counts. When something new or anomalous is detected, it
starts an OpenHands investigation conversation that diagnoses the problem,
optionally creates a PR fix, and posts a summary to Slack.

```
Every 15 min
     │
     ▼
Query Datadog ──► Match against known patterns ──► Update run_history
     │
     ├── Unknown logs? ──────────────────────────────────────────────┐
     │                                                               │
     └── Any pattern spiked (count > 3× baseline)?──────────────────┤
                                                                     │
                                                               Start one
                                                           investigation
                                                            conversation
                                                                     │
                                                    ┌────────────────┘
                                                    │
                                          Agent categorizes errors,
                                        investigates code, creates PR
                                        if confident, posts to Slack
```

## Prerequisites

- OpenHands running in local mode
- Datadog credentials: `DD_API_KEY` + `DD_APP_KEY` + `DD_SITE`
- Slack bot token: `SLACK_BOT_TOKEN` with `chat:write` scope
- Local code repositories (already cloned) for root-cause investigation
- Git host token (`GITHUB_PERSONAL_ACCESS_TOKEN`, `GITLAB_TOKEN`, or `BITBUCKET_TOKEN`) for PR creation

## Setup

Load this skill in OpenHands and it will guide you through a setup conversation:

1. Verify Datadog credentials and confirm your site region
2. Define the log query (tested live against your Datadog org)
3. Configure the Slack channel for summaries
4. Register local repository paths and git host tokens
5. Tune optional parameters (max log samples, examples per pattern, spike threshold)
6. Dry-run the query and confirm before deploying

The skill then packages and deploys the automation automatically.

## How patterns work

The pattern library is empty on first run — the system builds it organically:

- **First run:** All logs are uncategorized. The investigation agent groups them
  into named patterns with regex matchers and writes these to the state file.
- **Subsequent runs:** Logs are matched against known patterns. Only spikes or
  genuinely new error types trigger an investigation.
- **Over time:** The pattern library grows and stabilises. Investigations become
  rarer and more targeted.

Patterns are stored in the state file at:
```
~/.openhands/workspaces/automation-state/dd_monitor_{automation_id}.json
```

You can inspect and edit this file at any time to rename patterns, fix regexes,
or remove stale entries. Deleting the file resets the system.

## Token efficiency

The script itself is deterministic — no LLM calls on quiet runs. An OpenHands
conversation is only started when one of these conditions is met:
- At least one log event matched no known pattern
- At least one pattern's count exceeded `mean(last 3 runs) × spike_multiplier`

One conversation handles all triggers from a given run. A second conversation
cannot start until the first finishes.

## Files

| File | Purpose |
|---|---|
| `SKILL.md` | Step-by-step setup workflow for the OpenHands agent |
| `scripts/main.py` | Cron script template (customised at automation-creation time) |
| `references/state-schema.md` | State file JSON schema and agent write protocol |
| `references/datadog-api.md` | Datadog API reference (auth, log search, rate limits) |
| `references/agent-prompt-template.md` | Investigation prompt structure and token budget notes |
