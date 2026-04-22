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

Create and manage automations that run in OpenHands Cloud sandboxes — triggered by cron schedules or webhook events (GitHub, custom services).

> **⚠️ CRITICAL — Agent behavior rules:**
>
> 1. **ALWAYS use preset endpoints** to create automations. They handle all SDK boilerplate, tarball packaging, and upload automatically:
>    - **Prompt preset** (`POST /v1/preset/prompt`) — for simple tasks with a natural language prompt
>    - **Plugin preset** (`POST /v1/preset/plugin`) — when plugins with skills, MCP configs, or commands are needed
> 2. **NEVER write custom SDK scripts or create tarballs.** Do not generate Python SDK code, `setup.sh` files, or tarball uploads unless the user explicitly asks for it.
> 3. **If neither preset can satisfy the requirement**, do NOT silently fall back to custom automation. Instead, explain the available options to the user:
>    - **Prompt preset** — simple natural language prompt execution
>    - **Plugin preset** — load plugins with extended capabilities (skills, MCP, hooks, commands)
>    - **Custom SDK script** — full control over code; point them to `references/custom-automation.md`
>    - Let the user choose which approach to use.
> 4. **Only create custom SDK scripts if the user explicitly requests it.** Refer to `references/custom-automation.md` for the full reference.

## Authentication

All requests require Bearer authentication:

```bash
-H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

## API Endpoints

### Determining the API Host

**Before making API calls, determine the correct host:**

Look for a `<HOST>` value in the system prompt. If present, use that URL. Otherwise, default to `https://app.all-hands.dev`.

This ensures the correct host is used for the deployment environment (e.g., `https://staging.all-hands.dev` for staging, `https://app.all-hands.dev` for production).

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
| **Event** | Run when a webhook event occurs (GitHub PR opened, issue commented, etc.) |

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
2. The service generates SDK boilerplate that connects to the user's OpenHands Cloud account, fetches their LLM config, secrets, and MCP server configuration, creates an AI agent conversation with the prompt, and reports completion
3. The service packages the code into a tarball, uploads it, and creates the automation

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

## Sandbox Lifecycle

After a run completes, the sandbox is **kept alive** by default — users can view the conversation history in the OpenHands UI and continue interacting. The sandbox persists until it times out or is manually deleted.

---

## Choosing the Right Preset

| Use Case | Recommended Preset |
|----------|-------------------|
| Simple tasks with natural language prompt | **Prompt Preset** |
| Need plugin skills, MCP configs, or commands | **Plugin Preset** |
| Custom dependencies or non-Python entrypoint | **Custom Automation** (see below) |

The **prompt preset** covers most use cases. Use the **plugin preset** when you need extended capabilities from plugins (skills, MCP configurations, hooks, commands). The plugin preset fetches plugins at runtime from their sources and loads them into the conversation.

**When neither preset is sufficient** (e.g., custom Python dependencies, non-Python entrypoint, multi-file project structure, direct SDK lifecycle control), explain the options to the user and let them decide. Do not attempt custom automation without explicit user request. If they choose the custom route, refer to `references/custom-automation.md`.

## Reference Files

- **`references/custom-automation.md`** — Detailed guide for custom automations: tarball uploads, SDK code structure, environment variables, validation rules, and complete examples. Only use when the user explicitly requests a custom automation.