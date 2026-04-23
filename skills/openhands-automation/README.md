# Automation Skill

Create and manage OpenHands automations — scheduled tasks that run in sandboxes on a cron schedule.

## Triggers

This skill is activated by keywords:
- `automation` / `automations`
- `scheduled task`
- `cron job` / `cron schedule`

## Features

- **Prompt-based creation**: Create automations from a natural language prompt (recommended)
- **Automation management**: List, update, enable/disable, and delete automations
- **Manual dispatch**: Trigger automation runs on-demand
- **Custom automations**: For advanced users who need full control (see [references/custom-automation.md](references/custom-automation.md))

## API Base URL

All automation endpoints are at: `https://app.all-hands.dev/api/automation/v1`

## Quick Start

Create an automation with a single API call — just provide a name, prompt, and schedule:

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Report",
    "prompt": "Generate a daily status report and save it to the workspace",
    "trigger": {"type": "cron", "schedule": "0 9 * * 1-5", "timezone": "UTC"}
  }'
```

The service handles SDK code generation, tarball packaging, upload, and automation creation automatically.

## See Also

- [SKILL.md](SKILL.md) — Full API reference, agent behavior rules, and examples
- [references/custom-automation.md](references/custom-automation.md) — Reference for custom automations with user-provided SDK scripts
