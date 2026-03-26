---
allowed-tools: Bash(curl:*), Bash(tar:*), Bash(cat:*), Bash(echo:*), Bash(jq:*)
description: Create a new OpenHands automation with cron scheduling
---

# Create OpenHands Automation

Guide the user through creating a new automation interactively.

**API Base URL:** `https://app.all-hands.dev/api/automation/v1`

**Full API Reference:** See [skills/automation/SKILL.md](../../../skills/automation/SKILL.md) for complete documentation on endpoints, validation rules, SDK examples, and cron syntax.

## Workflow

### Step 1: Ask About Code Location

Ask the user if they:
1. **Have local code** - Needs to be uploaded as a tarball first
2. **Have an existing URL** - Already hosted (S3, GCS, HTTPS, or previous upload)

### Step 2: Upload Code (if needed)

If uploading local code:
```bash
# Create tarball
tar -czf automation.tar.gz -C /path/to/code .

# Upload (max 1MB)
curl -X POST "https://app.all-hands.dev/api/automation/v1/uploads?name=UPLOAD_NAME" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/gzip" \
  --data-binary @automation.tar.gz
```

Extract `tarball_path` from response (e.g., `oh-internal://uploads/{uuid}`).

### Step 3: Collect Required Fields

1. **Name**: Descriptive name (1-500 characters)
2. **Cron Schedule**: e.g., `0 9 * * 1` (Mondays at 9 AM UTC)
3. **Tarball Path**: `oh-internal://`, `s3://`, `gs://`, or `https://`
4. **Entrypoint**: e.g., `python main.py` or `uv run script.py`
5. **Timezone** (optional): IANA timezone (default: UTC)
6. **Setup Script** (optional): Relative path, e.g., `setup.sh`
7. **Timeout** (optional): 1-600 seconds (default: 600)

### Step 4: Create the Automation

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "USER_PROVIDED_NAME",
    "trigger": {
      "type": "cron",
      "schedule": "USER_PROVIDED_SCHEDULE",
      "timezone": "USER_PROVIDED_TIMEZONE_OR_UTC"
    },
    "tarball_path": "USER_PROVIDED_TARBALL_PATH",
    "entrypoint": "USER_PROVIDED_ENTRYPOINT"
  }'
```

### Step 5: Present Result

**On success (HTTP 201):** Show automation ID, name, schedule, and status.

**On error:** Show the error message from the API response.
