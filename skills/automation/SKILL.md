---
name: automation
description: This skill should be used when the user asks to "create an automation", "schedule a task", "set up a cron job", or mentions automations, scheduled tasks, or cron scheduling in OpenHands Cloud.
triggers:
- automation
- automations
- scheduled task
- cron job
- cron schedule
---

# OpenHands Automations

Create and manage scheduled tasks that run in OpenHands Cloud sandboxes on a cron schedule.

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

**Before making API calls, detect the correct host from the environment:**

```bash
# The host is available in OH_ALLOW_CORS_ORIGINS_0 (includes https://)
OPENHANDS_HOST="${OH_ALLOW_CORS_ORIGINS_0:-https://app.all-hands.dev}"
```

This automatically uses the correct host for the deployment environment (e.g., `https://staging.all-hands.dev` for staging, `https://app.all-hands.dev` for production).

### Endpoints

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
| `trigger.type` | Yes | Must be `"cron"` |
| `trigger.schedule` | Yes | Cron expression (5 fields: min hour day month weekday) |
| `trigger.timezone` | No | IANA timezone (default: `"UTC"`) |
| `timeout` | No | Max execution time in seconds (default: system maximum) |

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
| `trigger.type` | Yes | Must be `"cron"` |
| `trigger.schedule` | Yes | Cron expression (5 fields: min hour day month weekday) |
| `trigger.timezone` | No | IANA timezone (default: `"UTC"`) |
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