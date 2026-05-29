---
name: openhands-automation
description: This skill should be used when the user asks to "create an automation", "schedule a task", "set up a cron job", "webhook integration", "event-triggered automation", or mentions automations, scheduled tasks, cron scheduling, or webhook events in OpenHands Cloud.
triggers:
- automation
- automations
- scheduled task
- cron job
- cron schedule
- webhook
- webhooks
- event trigger
- github event
- pull request automation
- issue automation
- /automation:create
---

# OpenHands Automations

Create and manage automations that run inside an OpenHands agent server — triggered by cron schedules or webhook events (GitHub, custom services).

## Architecture

Two components work together to run automations:

**Automation Service** (API at `OPENHANDS_HOST/api/automation/v1`)
Manages the *when*: holds automation definitions, schedules cron-triggered runs, dispatches webhook-triggered runs, and receives completion callbacks to mark runs as done. This is the API you call to create, update, and manage automations.

**Agent Server** (accessible as `AGENT_SERVER_URL` inside script runs)
Manages the *what*: the runtime environment where automation scripts execute and where conversations (AI agent interactions with tools, bash, file editing, etc.) run. When a run is triggered, the automation service uploads the automation's tarball to the agent server, which unpacks and runs the entrypoint script. The script connects back to the agent server using `AGENT_SERVER_URL` and a session API key to start, monitor, and stop conversations.

The agent server typically runs inside a **sandbox** (a Docker or Kubernetes container). Some deployments use sandboxless mode, where the agent server runs directly on a host.

**Key environment variables:**

| Variable | Availability | Description |
|---|---|---|
| `RUNTIME_URL` | Ambient in cloud environments | Public-facing URL of the **agent server** sandbox. Use this to determine whether external webhook delivery is possible — if unset or local, webhooks cannot be received. The automation service may run at a separate URL (see Determining the API Host). |
| `AGENT_SERVER_URL` | Injected into scripts at run time only | Internal URL of the agent server. Available inside script execution context; **not** an ambient environment variable outside of a running script. |
| `OPENHANDS_HOST` | Shell convention only — set manually | Base URL for the automation service API. **Not a real environment variable.** Set it from the `<HOST>` system-prompt value, or default to `https://app.all-hands.dev`. Used in all `curl` examples throughout this skill. |

> **⚠️ CRITICAL — Agent behavior rules:**
>
> 0. **Does this task need an LLM at all? Check first.** Before picking a preset, ask whether the task actually requires reasoning, judgment, summarization, or open-ended tool use. If it is fully deterministic — fixed data transforms, scheduled HTTP calls, healthcheck pings, file rotation, picking from a known list, posting a templated message — an LLM-driven preset is overkill. Every run will consume LLM tokens, which adds up fast at high frequencies (every 5 min ≈ 288 runs/day). Surface the trade-off to the user and offer the custom-script path (see `references/custom-automation.md`) as the cheaper, more reliable option. Be especially careful for cron schedules tighter than hourly.
>
>    **Instant-recognition patterns — these are always deterministic, never use an LLM preset:**
>    - "post a quote / message / fact every N minutes" (rotating from a list)
>    - "send a scheduled reminder / standup / digest"
>    - "ping a health-check URL on a schedule"
>    - "post to Slack / webhook every N minutes"
>    - Any task where the full output could be written as a static template right now
>
> 1. **For LLM-appropriate work, default to preset endpoints.** They handle all SDK boilerplate, tarball packaging, and upload automatically:
>    - **Prompt preset** (`POST /v1/preset/prompt`) — for tasks expressed as a natural language prompt that benefit from agent reasoning
>    - **Plugin preset** (`POST /v1/preset/plugin`) — when plugins with skills, MCP configs, or commands are needed
> 2. **Do not silently create custom scripts.** Do not generate Python code, `setup.sh` files, or tarball uploads without user consent. But *do* proactively recommend the custom path (per rule 0) when the task is deterministic or high-frequency — surface the option and let the user choose.
> 3. **If neither preset is the right fit**, do NOT silently fall back to custom automation. Instead, explain the available options to the user:
>    - **Prompt preset** — natural language prompt execution (LLM-driven)
>    - **Plugin preset** — load plugins with extended capabilities (skills, MCP, hooks, commands)
>    - **Custom script** — full control over code, with or without LLM; point them to `references/custom-automation.md`
>    - Let the user choose which approach to use.
> 4. **Only create custom scripts after the user agrees to that path.** Refer to `references/custom-automation.md` for the full reference.
> 5. **Before suggesting event-triggered (webhook) automations, check whether the deployment is publicly reachable.** Check `RUNTIME_URL`. Webhooks require an internet-accessible URL so that external services (GitHub, Slack, Linear, etc.) can deliver events to the automation service. If `RUNTIME_URL` is unset, empty, or resolves to a local or private address (`localhost`, `127.0.0.1`, `0.0.0.0`, or any RFC 1918 range: `10.x.x.x`, `192.168.x.x`, `172.16–31.x.x`), the service cannot receive inbound webhook traffic from the public internet. In that case:
>    - **Recommend a cron-based polling automation instead.** Have the automation run on a schedule and call the external service's API (e.g., the GitHub REST API) to check for new events since the last run.
>    - Explain the limitation clearly to the user: "Because this is a local deployment, external services can't reach the webhook endpoint. I'll set up a polling automation using a cron schedule instead."

### No-LLM Script Helpers

When building a deterministic custom script, these two stdlib-only functions are required. Copy them verbatim — they use `AGENT_SERVER_URL` and `SESSION_API_KEY` injected by the automation service.

```python
import json, os, urllib.request

def get_secret(name):
    """Fetch a named secret stored in the agent server."""
    url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    key = os.environ.get("SESSION_API_KEY") or os.environ.get("OH_SESSION_API_KEYS_0", "")
    with urllib.request.urlopen(urllib.request.Request(
        f"{url}/api/settings/secrets/{name}", headers={"X-Session-API-Key": key}
    )) as r:
        return r.read().decode().strip()

def fire_callback(status="COMPLETED", error=None):
    """Signal run completion. MUST be called on every exit path — success AND error."""
    url = os.environ.get("AUTOMATION_CALLBACK_URL", "")
    if not url: return
    body = {"status": status, "run_id": os.environ.get("AUTOMATION_RUN_ID", "")}
    if error: body["error"] = error
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body).encode(), headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('AUTOMATION_CALLBACK_API_KEY', '')}",
        }))
    except Exception as e: print(f"Callback error: {e}")
```

Entrypoint must be `python3 main.py` (no `setup.sh` needed). Wrap your main logic in `try/except` and call `fire_callback("FAILED", str(e))` in the except block.

---

## Authentication

All requests require Bearer authentication:

```bash
-H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

## API Endpoints

### Determining the API Host

**Before making API calls, determine the correct host:**

The automation service may run at a different URL from the agent server. In the examples throughout this skill, `${OPENHANDS_HOST}` is a shell-variable convention for the automation service base URL — it is **not** a real environment variable. Set it from context before running any curl command:

- Look for a `<HOST>` value in the system prompt. If present, use that URL.
- Otherwise default to `https://app.all-hands.dev`.

```bash
OPENHANDS_HOST="https://app.all-hands.dev"  # replace with <HOST> if provided
```


### Automation Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/automation/v1/preset/prompt` | POST | **Create automation from a prompt (recommended)** |
| `/api/automation/v1/preset/plugin` | POST | **Create automation with plugins** |
| `/api/automation/v1` | GET | List automations |
| `/api/automation/v1/{id}` | GET | Get automation details |
| `/api/automation/v1/{id}` | PATCH | Update automation |
| `/api/automation/v1/{id}` | DELETE | Delete automation |
| `/api/automation/v1/{id}/dispatch` | POST | Trigger a run manually |
| `/api/automation/v1/{id}/runs` | GET | List automation runs |

### Custom Webhook Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/automation/v1/webhooks` | POST | Register a custom webhook source |
| `/api/automation/v1/webhooks` | GET | List all custom webhooks |
| `/api/automation/v1/webhooks/{id}` | GET | Get webhook details |
| `/api/automation/v1/webhooks/{id}` | PATCH | Update webhook settings |
| `/api/automation/v1/webhooks/{id}` | DELETE | Delete a webhook |
| `/api/automation/v1/webhooks/{id}/rotate-secret` | POST | Rotate signing secret |

---

## Trigger Types

Automations support two trigger types:

| Trigger Type | Use Case |
|--------------|----------|
| **Cron** | Run on a schedule (daily, weekly, hourly, etc.) |
| **Event** | Run when a webhook event occurs (GitHub PR opened, issue commented, etc.) — **requires a publicly reachable deployment** |

---

## Creating Automations

Two preset endpoints simplify automation creation by handling SDK boilerplate, tarball packaging, and upload automatically:

1. **Prompt Preset** — Execute a natural language prompt (simple tasks)
2. **Plugin Preset** — Load plugins with skills, MCP configs, and commands (extended capabilities)

---

### Prompt Preset

Use the **preset/prompt endpoint** for simple automations. Provide a natural language prompt describing the task.

#### How It Works

1. Send a prompt describing the task (e.g., "Generate a weekly status report")
2. The automation service generates a Python script that: fetches LLM config and secrets from the agent server, starts an AI agent conversation with your prompt, and sends a completion callback when done
3. The script is packaged as a tarball and the automation is registered; on each trigger, the automation service uploads the tarball to the agent server, which unpacks and runs the script inside its environment

#### Request

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Automation Name",
    "prompt": "What the automation should do",
    "trigger": {
      "type": "cron",
      "schedule": "0 9 * * *",
      "timezone": "UTC"
    }
  }'
```

#### Request Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Name of the automation (1-500 characters) |
| `prompt` | Yes | Natural language instructions (1-50,000 characters) |
| `trigger` | Yes | Trigger configuration — either `cron` or `event` (see below) |
| `timeout` | No | Max execution time in seconds (default: system maximum) |
| `repos` | No | Repositories to clone (see [Repository Cloning](#repository-cloning)) |

**Cron Trigger Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `trigger.type` | Yes | `"cron"` |
| `trigger.schedule` | Yes | Cron expression (5 fields: min hour day month weekday) |
| `trigger.timezone` | No | IANA timezone (default: `"UTC"`) |

**Event Trigger Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `trigger.type` | Yes | `"event"` |
| `trigger.source` | Yes | Event source: `"github"` or custom webhook source name |
| `trigger.on` | Yes | Event key pattern(s) to match (see Event Keys below) |
| `trigger.filter` | No | JMESPath expression for payload filtering (see Filter Expressions below) |

#### Prompt Tips

Write the prompt as an instruction to an AI agent. The prompt executes inside a sandbox with full tool access (bash, file editing, etc.), the user's configured LLM, stored secrets, and MCP server integrations. Examples:

- `"Generate a weekly status report summarizing the team's GitHub activity and post it to Slack"`
- `"Check the production API health endpoint every hour and alert if it returns non-200"`
- `"Pull the latest data from our analytics API and update the dashboard spreadsheet"`

#### Cron Schedule

| Field | Values | Description |
|-------|--------|-------------|
| Minute | 0-59 | Minute of the hour |
| Hour | 0-23 | Hour of the day (24-hour) |
| Day | 1-31 | Day of the month |
| Month | 1-12 | Month of the year |
| Weekday | 0-6 | Day of week (0=Sun, 6=Sat) |

Common schedules: `0 9 * * *` (daily 9 AM), `0 9 * * 1-5` (weekdays 9 AM), `0 9 * * 1` (Mondays 9 AM), `0 0 1 * *` (first of month), `*/15 * * * *` (every 15 min), `0 */6 * * *` (every 6 hours).

#### Response (HTTP 201)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "My Automation Name",
  "trigger": {"type": "cron", "schedule": "0 9 * * *", "timezone": "UTC"},
  "enabled": true,
  "created_at": "2025-03-25T10:00:00Z"
}
```

#### Prompt Preset Examples

**Daily report:**
```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Report",
    "prompt": "Generate a daily status report and save it to a file in the workspace",
    "trigger": {"type": "cron", "schedule": "0 9 * * 1-5", "timezone": "America/New_York"}
  }'
```

**Weekly cleanup:**
```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weekly Cleanup",
    "prompt": "Clean up temporary files older than 7 days and send a summary of what was removed",
    "trigger": {"type": "cron", "schedule": "0 2 * * 0", "timezone": "UTC"},
    "timeout": 300
  }'
```

---

## Polling as a Webhook Alternative

When the deployment cannot receive inbound webhook traffic (see rule 5), use a cron-triggered automation that calls the external service’s API on a schedule to check for new events.

### Polling vs. Webhooks at a Glance

| | Webhooks (Event trigger) | Polling (Cron trigger) |
|---|---|---|
| **Requires public URL** | Yes | No — works locally |
| **Latency** | Near-instant | Up to one poll interval |
| **API calls** | Only on real events | Every poll interval |
| **Best for** | Cloud / public deployments | Local or private deployments |

---

## Event-Triggered Automations (Webhooks)

Event-triggered automations run when a webhook event occurs — like a GitHub PR being opened, an issue receiving a comment, or a custom service sending a notification.

### Built-in Integrations

**GitHub** is a built-in integration — no webhook registration needed. Just create automations with `"source": "github"`.

### GitHub Event Keys

Events use the format `{event_type}.{action}` or just `{event_type}` (for events without actions like `push`).

| Event Type | Event Keys | Description |
|------------|------------|-------------|
| `pull_request` | `pull_request.opened`, `pull_request.closed`, `pull_request.synchronize`, `pull_request.labeled`, `pull_request.unlabeled`, `pull_request.reopened`, `pull_request.edited`, `pull_request.ready_for_review` | PR activity |
| `issues` | `issues.opened`, `issues.closed`, `issues.reopened`, `issues.labeled`, `issues.unlabeled`, `issues.edited`, `issues.assigned` | Issue activity |
| `issue_comment` | `issue_comment.created`, `issue_comment.edited`, `issue_comment.deleted` | Comments on issues/PRs |
| `push` | `push` | Code pushed to a branch |
| `release` | `release.published`, `release.created`, `release.released`, `release.prereleased` | Release activity |
| `pull_request_review` | `pull_request_review.submitted`, `pull_request_review.edited`, `pull_request_review.dismissed` | PR review activity |

**Wildcards:** Use `*` to match any action — e.g., `pull_request.*` matches all PR events.

**Multiple patterns:** The `on` field can be a string or array — e.g., `["push", "pull_request.opened"]`.

### Filter Expressions (JMESPath)

Filters let you match events based on payload content using JMESPath expressions.

#### Available Functions

| Function | Description | Example |
|----------|-------------|---------|
| `glob(str, pattern)` | Wildcard pattern matching | `glob(repository.full_name, 'myorg/*')` |
| `icontains(str, substr)` | Case-insensitive substring | `icontains(comment.body, '@openhands')` |
| `contains(array, value)` | Array contains value | `contains(pull_request.labels[].name, 'bug')` |
| `regex(str, pattern)` | Regular expression match | `regex(ref, '^refs/tags/v\\d+')` |
| `starts_with(str, prefix)` | String starts with | `starts_with(ref, 'refs/heads/')` |
| `ends_with(str, suffix)` | String ends with | `ends_with(ref, '/main')` |
| `lower(str)` / `upper(str)` | Case conversion | `lower(sender.login) == 'admin'` |

#### Boolean Operators

- `&&` — AND
- `||` — OR  
- `!` — NOT

#### Filter Examples

```javascript
// Exact match on label name
"contains(pull_request.labels[].name, 'openhands')"

// Case-insensitive mention in comment
"icontains(comment.body, '@openhands')"

// Match specific repository
"repository.full_name == 'myorg/myrepo'"

// Match any repo in an org
"glob(repository.full_name, 'myorg/*')"

// PR with 'bug' label in any org repo
"glob(repository.full_name, 'myorg/*') && contains(pull_request.labels[].name, 'bug')"

// Push to main or release branches
"glob(ref, 'refs/heads/main') || glob(ref, 'refs/heads/release/*')"

// Issue opened by a specific user
"sender.login == 'dependabot[bot]'"

// Not a draft PR
"!pull_request.draft"
```

---

### Event-Triggered Examples

#### GitHub: Respond to @openhands mentions in comments

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenHands Mention Responder",
    "prompt": "Analyze the issue or PR context and provide a helpful response to the user'\''s question. The comment body and context are available in the event payload.",
    "trigger": {
      "type": "event",
      "source": "github",
      "on": "issue_comment.created",
      "filter": "icontains(comment.body, '\''@openhands'\'')"
    },
    "timeout": 300
  }'
```

#### GitHub: Auto-review PRs with the "openhands" label

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Auto Review PRs",
    "prompt": "Review this pull request for code quality, potential bugs, and best practices. Provide constructive feedback.",
    "trigger": {
      "type": "event",
      "source": "github",
      "on": "pull_request.labeled",
      "filter": "contains(pull_request.labels[].name, '\''openhands'\'')"
    }
  }'
```

#### GitHub: Run tests on push to main

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Run Tests on Main",
    "prompt": "Clone the repository and run the test suite. Report any failures.",
    "trigger": {
      "type": "event",
      "source": "github",
      "on": "push",
      "filter": "ref == '\''refs/heads/main'\''"
    }
  }'
```

#### GitHub: Triage new issues in specific repos

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Issue Triage Bot",
    "prompt": "Analyze this new issue and suggest appropriate labels. If it looks like a bug, try to identify the root cause.",
    "trigger": {
      "type": "event",
      "source": "github",
      "on": "issues.opened",
      "filter": "glob(repository.full_name, '\''myorg/*'\'')"
    }
  }'
```

#### GitHub: Respond to multiple event types

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "PR Activity Bot",
    "prompt": "Process the PR event and take appropriate action based on the event type.",
    "trigger": {
      "type": "event",
      "source": "github",
      "on": ["pull_request.opened", "pull_request.synchronize", "pull_request.ready_for_review"]
    }
  }'
```

---

## Custom Webhooks

For services other than GitHub (Linear, Stripe, Slack, etc.), register a custom webhook first.

> **Agent behavior:**
> - **Always provide the curl request** to the user — do not attempt to register webhooks yourself.
> - **Ask the user:** "Do you have a webhook signing secret from [service], or should the system generate one?"
>   - If they have one → include `webhook_secret` in the request
>   - If not → omit it; the response will contain a generated secret they must configure in their service

### Register a Custom Webhook

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/webhooks" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Linear Issues",
    "source": "linear",
    "event_key_expr": "type",
    "signature_header": "Linear-Signature",
    "webhook_secret": "your-linear-webhook-secret"
  }'
```

#### Webhook Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Human-readable name for the webhook |
| `source` | Yes | Unique source identifier (lowercase, alphanumeric with hyphens, 1-50 chars) |
| `event_key_expr` | No | JMESPath expression to extract event type from payload (default: `"type"`) |
| `signature_header` | No | HTTP header containing HMAC signature (default: `"X-Signature-256"`) |
| `webhook_secret` | No | Signing secret — provide your own (from the external service) or let the system generate one |

#### Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "webhook_url": "https://app.all-hands.dev/v1/events/{org_id}/linear",
  "source": "linear",
  "enabled": true
}
```

**Note:** When you provide your own `webhook_secret`, it won't be echoed back in the response. If you don't provide one, the system generates a secret and returns it once — store it securely.

### Manage Custom Webhooks

```bash
# List all webhooks
curl "${OPENHANDS_HOST}/api/automation/v1/webhooks" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"

# Update a webhook
curl -X PATCH "${OPENHANDS_HOST}/api/automation/v1/webhooks/{webhook_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Rotate the signing secret
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/webhooks/{webhook_id}/rotate-secret" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"

# Delete a webhook
curl -X DELETE "${OPENHANDS_HOST}/api/automation/v1/webhooks/{webhook_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Custom Webhook Example: Linear

Linear sends webhooks with:
- Signature header: `Linear-Signature`
- Event type in payload: `type` field (e.g., `Issue`, `Comment`, `Project`)
- Action in payload: `action` field (e.g., `create`, `update`, `remove`)

```bash
# 1. Register the Linear webhook
#    - Get your webhook signing secret from Linear's webhook settings
#    - Use "Linear-Signature" as the signature header
#    - Use "type" to extract the event type from the payload
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/webhooks" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Linear Issues",
    "source": "linear",
    "event_key_expr": "type",
    "signature_header": "Linear-Signature",
    "webhook_secret": "lin_wh_xxxxxxxxxxxxx"
  }'

# Response includes webhook_url — configure this in Linear:
# Settings → API → Webhooks → New webhook → paste the webhook_url

# 2. Create an automation for new Linear issues
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Triage New Linear Issues",
    "prompt": "A new issue was created in Linear. Analyze the issue title and description, suggest appropriate labels, and add a comment with initial triage notes.",
    "trigger": {
      "type": "event",
      "source": "linear",
      "on": "Issue",
      "filter": "action == '\''create'\''"
    }
  }'

# 3. Create an automation for high-priority issue updates
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High Priority Issue Alert",
    "prompt": "A high-priority issue was updated. Review the changes and notify the team if action is needed.",
    "trigger": {
      "type": "event",
      "source": "linear",
      "on": "Issue",
      "filter": "action == '\''update'\'' && data.priority == `1`"
    }
  }'
```

### Common Signature Headers by Service

| Service | Signature Header | Event Key Expression |
|---------|-----------------|---------------------|
| Linear | `Linear-Signature` | `type` |
| Stripe | `Stripe-Signature` | `type` |
| Slack | `X-Slack-Signature` | `type` |
| Twilio | `X-Twilio-Signature` | `type` |
| Generic | `X-Signature-256` | `type` |

---

### Plugin Preset

Use the **preset/plugin endpoint** when you need to load one or more plugins that provide extended capabilities like skills, MCP configurations, hooks, and commands.

> **💡 Finding plugins:** Browse the [OpenHands/extensions](https://github.com/OpenHands/extensions) repository for available skills and plugins. When given a broad use case, check this directory first to see if something already exists that fits your needs.

#### How It Works

1. Specify one or more plugins (from GitHub repos, git URLs, or monorepo subdirectories)
2. Provide a prompt that can invoke plugin commands (e.g., `/plugin-name:command`)
3. The service generates SDK boilerplate that loads all plugins at runtime, creates a conversation with plugin capabilities, and executes the prompt
4. The service packages everything into a tarball, uploads it, and creates the automation

#### Request

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/plugin" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Plugin Automation",
    "plugins": [
      {"source": "github:owner/repo", "ref": "v1.0.0"},
      {"source": "github:owner/another-plugin"}
    ],
    "prompt": "Use the plugin commands to perform the task",
    "trigger": {
      "type": "cron",
      "schedule": "0 9 * * 1",
      "timezone": "UTC"
    }
  }'
```

#### Request Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Name of the automation (1-500 characters) |
| `plugins` | Yes | List of plugin sources (at least one required) |
| `plugins[].source` | Yes | Plugin source: `github:owner/repo`, git URL, or local path |
| `plugins[].ref` | No | Git ref: branch, tag, or commit SHA |
| `plugins[].repo_path` | No | Subdirectory path for monorepos |
| `prompt` | Yes | Instructions for the automation (1-50,000 characters) |
| `trigger` | Yes | Trigger configuration — either `cron` or `event` (same as Prompt Preset) |
| `timeout` | No | Max execution time in seconds (default: system maximum) |
| `repos` | No | Repositories to clone (see [Repository Cloning](#repository-cloning)) |

#### Plugin Source Formats

| Format | Example | Description |
|--------|---------|-------------|
| GitHub shorthand | `github:owner/repo` | Fetches from GitHub |
| Git URL | `https://github.com/owner/repo.git` | Any git repository |
| With ref | `{"source": "github:owner/repo", "ref": "v1.0.0"}` | Specific branch/tag/commit |
| Monorepo | `{"source": "github:org/monorepo", "repo_path": "plugins/my-plugin"}` | Subdirectory in repo |

#### Response (HTTP 201)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "My Plugin Automation",
  "trigger": {"type": "cron", "schedule": "0 9 * * 1", "timezone": "UTC"},
  "enabled": true,
  "created_at": "2025-03-25T10:00:00Z"
}
```

#### Plugin Preset Examples

**Single plugin with version:**
```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/plugin" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Code Review Automation",
    "plugins": [
      {"source": "github:owner/code-review-plugin", "ref": "v2.0.0"}
    ],
    "prompt": "Review all Python files in the repository for code quality issues",
    "trigger": {"type": "cron", "schedule": "0 9 * * 1-5", "timezone": "UTC"}
  }'
```

**Multiple plugins:**
```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/plugin" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Security Scan Automation",
    "plugins": [
      {"source": "github:owner/security-scanner"},
      {"source": "github:owner/report-generator", "ref": "main"}
    ],
    "prompt": "Run a security scan on the codebase and generate a report",
    "trigger": {"type": "cron", "schedule": "0 2 * * 0", "timezone": "UTC"},
    "timeout": 600
  }'
```

**Monorepo plugin:**
```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/plugin" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Style Guide Enforcement",
    "plugins": [
      {"source": "github:company/monorepo", "repo_path": "plugins/style-guide", "ref": "main"}
    ],
    "prompt": "Check all files against the company style guide",
    "trigger": {"type": "cron", "schedule": "0 8 * * 1", "timezone": "America/Los_Angeles"}
  }'
```

---

## Repository Cloning

Both presets support an optional `repos` field to clone repositories into the sandbox before execution. Cloned repos have their skills (AGENTS.md, `.agents/skills/`) automatically loaded.

### Repo Source Formats

| Format | Example | Description |
|--------|---------|-------------|
| Full URL | `"https://github.com/owner/repo"` | Provider auto-detected |
| Full URL + ref | `{"url": "https://github.com/owner/repo", "ref": "main"}` | With branch/tag/SHA |
| Short URL | `{"url": "owner/repo", "provider": "github"}` | Requires `provider` field |

**Supported providers:** `github`, `gitlab`, `bitbucket`

> **Note:** Short URLs (`owner/repo`) require an explicit `provider` field. Full URLs auto-detect the provider.

### Examples

**Single repo (full URL):**
```json
{
  "repos": ["https://github.com/OpenHands/openhands-cli"]
}
```

**Multiple repos with refs:**
```json
{
  "repos": [
    {"url": "https://github.com/owner/repo1", "ref": "main"},
    {"url": "https://gitlab.com/owner/repo2", "ref": "v1.0.0"}
  ]
}
```

**Short URL with provider:**
```json
{
  "repos": [
    {"url": "owner/repo", "provider": "github", "ref": "main"}
  ]
}
```

### Complete Automation Example

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Analyze Codebase",
    "prompt": "Analyze the openhands-cli codebase and generate a summary report",
    "trigger": {"type": "cron", "schedule": "0 9 * * 1"},
    "repos": [
      {"url": "https://github.com/OpenHands/openhands-cli", "ref": "main"}
    ]
  }'
```

---

## Managing Automations

### List Automations

```bash
curl "${OPENHANDS_HOST}/api/automation/v1?limit=20" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Get / Update / Delete

```bash
# Get details
curl "${OPENHANDS_HOST}/api/automation/v1/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"

# Update (fields: name, trigger, enabled, timeout)
curl -X PATCH "${OPENHANDS_HOST}/api/automation/v1/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Delete
curl -X DELETE "${OPENHANDS_HOST}/api/automation/v1/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Trigger and Monitor Runs

```bash
# Manually trigger a run
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/{automation_id}/dispatch" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"

# List runs
curl "${OPENHANDS_HOST}/api/automation/v1/{automation_id}/runs?limit=20" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

Run status values: `PENDING` (waiting for dispatch), `RUNNING` (in progress), `COMPLETED` (success), `FAILED` (check `error_detail`).

---

## Run Lifecycle

When a run completes, the automation service receives a callback and marks the run done. Any conversations started during the run remain accessible in the OpenHands UI — users can view the history and continue interacting. The agent server persists until it times out or is manually deleted.

The automation script itself controls when the callback fires (signalling completion). For simple synchronous scripts this happens naturally on exit. For scripts that start asynchronous conversations, the callback should be deferred until the conversation reaches an idle state (see `references/custom-automation.md` for patterns).

---

## Choosing the Right Preset

Pick based on **what the task needs**, not just **what is technically possible**. An LLM-driven preset can do almost anything, so "the preset can satisfy this" is not by itself a good reason to pick it — every run costs tokens and sandbox time.

| Use Case | Recommended |
|----------|-------------|
| Reasoning, summarization, triage, code review, or open-ended tool use | **Prompt Preset** |
| Needs plugin commands / skills / MCP configs / hooks | **Plugin Preset** |
| Compare plugin versions or configurations across runs | **Plugin Preset with A/B testing** — see `references/ab-testing.md` |
| **Deterministic task** (fixed data + scheduled action, e.g. healthcheck, Slack notification, rotating from a known list) — especially if it runs frequently | **Custom script, no LLM** — see `references/custom-automation.md#deterministic-script-no-llm` |
| Custom Python dependencies, multi-file project, or direct SDK lifecycle control | **Custom script with SDK** — see `references/custom-automation.md#sdk-based-scripts` |

The **prompt preset** is the right default for genuinely agent-shaped work — anything that benefits from reasoning over context, calling tools dynamically, or producing a non-templated output. Use the **plugin preset** when you need extended capabilities from plugins (skills, MCP configurations, hooks, commands).

**Watch for deterministic, high-frequency patterns.** Requests like "send a daily standup reminder", "ping a healthcheck URL every minute", "post a random quote every 5 minutes", or "rotate a fact-of-the-day message" do not need an LLM. Surface this to the user explicitly with a rough cost framing (e.g. "this schedule will invoke your LLM ~288 times/day") before defaulting to a preset. As a rule of thumb, any cron tighter than hourly deserves a deliberate "should this really be agent-driven?" check.

**When neither preset is the right fit** (deterministic task, custom Python dependencies, non-Python entrypoint, multi-file project structure, direct SDK lifecycle control), explain the options to the user and let them decide. Do not attempt custom automation without explicit user agreement. If they choose the custom route, refer to `references/custom-automation.md`.

## Reference Files

- **`references/custom-automation.md`** — Detailed guide for custom automations: tarball uploads, code structure (SDK and no-LLM), environment variables, validation rules, and complete examples. Consult this whenever you need to evaluate or recommend the custom path (including for deterministic / cost-sensitive tasks per rule 0). Only *implement* a custom automation after the user agrees to that path.
- **`references/ab-testing.md`** — A/B testing for plugin automations: defining variants with weights, experiment configuration, variant selection logic, observability via conversation tags, and complete examples. Consult this when a user wants to compare plugin versions or configurations.
