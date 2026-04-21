---
allowed-tools: Bash(curl:*), Bash(cat:*), Bash(echo:*), Bash(jq:*)
description: Create a new OpenHands automation with cron scheduling
---

# Create OpenHands Automation

Guide the user through creating a new automation interactively.

**API Base URL:** `https://app.all-hands.dev/api/automation/v1`

**Full API Reference:** See [skills/openhands-automation/SKILL.md](../../../skills/openhands-automation/SKILL.md) for complete documentation.

> **⚠️ CRITICAL:** Always use the **preset/prompt endpoint** to create automations. Do NOT write custom SDK scripts or create tarballs unless the user explicitly requests it. If the prompt approach cannot meet the user's needs, explain the available options and let them choose.

## Workflow

### Step 1: Understand What the User Wants

Ask the user to describe what the automation should do. In most cases, the user's description can be used directly as the prompt for the preset endpoint.

### Step 2: Collect Required Fields

1. **Name**: Descriptive name for the automation (1-500 characters)
2. **Prompt**: What the automation should do — use the user's description
3. **Cron Schedule**: e.g., `0 9 * * 1` (Mondays at 9 AM UTC)
4. **Timezone** (optional): IANA timezone (default: UTC)
5. **Timeout** (optional): Max execution time in seconds

### Step 3: Create the Automation

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "USER_PROVIDED_NAME",
    "prompt": "USER_PROVIDED_DESCRIPTION_OF_WHAT_TO_DO",
    "trigger": {
      "type": "cron",
      "schedule": "USER_PROVIDED_SCHEDULE",
      "timezone": "USER_PROVIDED_TIMEZONE_OR_UTC"
    }
  }'
```

### Step 4: Present Result

**On success (HTTP 201):** Show automation ID, name, schedule, and status.

**On error:** Show the error message from the API response.

### If the Preset Is Not Enough

If the user needs custom dependencies, a non-Python entrypoint, or full control over the SDK code, explain the options and let them decide. If they choose a custom automation, refer to [references/custom-automation.md](../../../skills/openhands-automation/references/custom-automation.md) for the tarball upload and custom creation workflow.
