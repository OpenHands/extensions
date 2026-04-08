# Automation Skill

Create and manage OpenHands automations — tasks that run in sandboxes on a cron schedule or triggered by webhook events (GitHub, custom services).

## Triggers

This skill is activated by keywords:
- `automation` / `automations`
- `scheduled task`
- `cron job` / `cron schedule`
- `webhook` / `webhooks`
- `event trigger`
- `github event`
- `pull request automation`
- `issue automation`

## Features

- **Prompt-based creation**: Create automations from a natural language prompt (recommended)
- **Event-triggered automations**: Trigger on GitHub events (PR opened, issue commented, push, etc.)
- **Custom webhooks**: Register webhooks for any service (Stripe, Slack, Linear, etc.)
- **JMESPath filters**: Match events based on payload content (labels, mentions, repos)
- **Automation management**: List, update, enable/disable, and delete automations
- **Manual dispatch**: Trigger automation runs on-demand
- **Custom automations**: For advanced users who need full control (see [references/custom-automation.md](references/custom-automation.md))

## API Base URL

All automation endpoints are at: `https://app.all-hands.dev/api/automation/v1`

## Quick Start

### Cron-Triggered Automation

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

### Event-Triggered Automation (GitHub)

Respond to @openhands mentions in issue comments:

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mention Responder",
    "prompt": "Analyze the issue context and respond helpfully",
    "trigger": {
      "type": "event",
      "source": "github",
      "on": "issue_comment.created",
      "filter": "icontains(comment.body, '\''@openhands'\'')"
    }
  }'
```

Auto-review PRs with the "openhands" label:

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Auto Review PRs",
    "prompt": "Review this PR for code quality and best practices",
    "trigger": {
      "type": "event",
      "source": "github",
      "on": "pull_request.labeled",
      "filter": "contains(pull_request.labels[].name, '\''openhands'\'')"
    }
  }'
```

The service handles SDK code generation, tarball packaging, upload, and automation creation automatically.

## See Also

- [SKILL.md](SKILL.md) — Full API reference, agent behavior rules, event keys, filters, and examples
- [references/custom-automation.md](references/custom-automation.md) — Reference for custom automations with user-provided SDK scripts
