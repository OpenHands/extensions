---
allowed-tools: Bash(curl:*), Bash(tar:*), Bash(cat:*), Bash(echo:*), Bash(jq:*)
description: Create a new OpenHands automation with cron scheduling
---

# Create OpenHands Automation

Guide the user through creating a new automation that runs on a cron schedule.

## API Base URL

All automation endpoints are at: `https://app.all-hands.dev/api/automation/v1`

## Instructions

Help the user create an automation by collecting the required information interactively.

### Step 0: Ask About Code Location

First, ask the user if they:
1. **Have code to upload** - They have local files that need to be uploaded as a tarball
2. **Have an existing tarball URL** - They already have code hosted somewhere (S3, GCS, HTTPS, or a previous upload)

If they need to upload code, guide them through the upload process first (see Step 1a).
If they have an existing URL, skip to Step 1b.

### Step 1a: Upload Code (if needed)

If the user has local code to upload:

1. Help them create a tarball from their code:
   ```bash
   tar -czf automation.tar.gz -C /path/to/code .
   ```

2. Upload the tarball (max 1MB):
   ```bash
   curl -X POST "https://app.all-hands.dev/api/automation/v1/uploads?name=UPLOAD_NAME" \
     -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
     -H "Content-Type: application/gzip" \
     --data-binary @automation.tar.gz
   ```

3. Extract the `tarball_path` from the response:
   ```bash
   # Response includes: "tarball_path": "oh-internal://uploads/{uuid}"
   ```

4. Verify the upload status is `COMPLETED` before proceeding.

**Upload Constraints:**
- Maximum file size: 1MB
- Allowed content types: `application/gzip`, `application/x-tar`, `application/x-gzip`, `application/x-compressed-tar`, `application/octet-stream`

### Step 1b: Collect Automation Details

Ask the user for each of these fields:

1. **Name** (required): A descriptive name for the automation (1-500 characters)

2. **Cron Schedule** (required): When the automation should run
   - Examples: `0 9 * * *` (daily at 9 AM), `0 9 * * 5` (Fridays at 9 AM)
   - Provide helpful examples based on what the user describes

3. **Timezone** (optional): IANA timezone name (default: UTC)
   - Examples: `America/New_York`, `Europe/London`, `Asia/Tokyo`

4. **Tarball Path** (required if not uploaded): Location of the code to run
   - Internal upload: `oh-internal://uploads/{uuid}` (from Step 1a)
   - S3: `s3://bucket/path/file.tar.gz`
   - GCS: `gs://bucket/path/file.tar.gz`
   - HTTPS: `https://example.com/file.tar.gz`

5. **Entrypoint** (required): Command to execute
   - Examples: `uv run main.py`, `python script.py`, `./run.sh`
   - Must be a relative path, no shell metacharacters

6. **Setup Script Path** (optional): Relative path to setup script inside tarball
   - Example: `setup.sh`

7. **Timeout** (optional): Maximum execution time in seconds
   - Range: 1-600 seconds (default: 600 = 10 minutes)
   - Only positive integers allowed

### Step 2: Validate the Information

Before creating, validate:
- Name is not empty and ≤ 500 characters
- Cron schedule is valid (5 fields: minute hour day month weekday)
- Tarball path starts with `oh-internal://`, `s3://`, `gs://`, `http://`, or `https://`
- Entrypoint is a relative path without `..` or shell metacharacters (`;`, `&`, `|`, etc.)
- Timeout (if provided) is between 1 and 600

### Step 3: Create the Automation

Use the OpenHands Automations API to create the automation:

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
    "entrypoint": "USER_PROVIDED_ENTRYPOINT",
    "setup_script_path": "USER_PROVIDED_OR_NULL",
    "timeout": USER_PROVIDED_OR_NULL
  }'
```

Replace placeholders with actual values. Omit `setup_script_path` and `timeout` if not provided.

### Step 4: Present the Result

On success (HTTP 201), display:
- ✅ Automation created successfully!
- **ID**: The automation UUID
- **Name**: The name provided
- **Schedule**: Human-readable description of the cron schedule
- **Timezone**: The timezone
- **Status**: Enabled

On error (HTTP 4xx/5xx), display:
- ❌ Failed to create automation
- The error message from the API response

## Cron Schedule Reference

Help users construct cron schedules:

| Field | Values | Description |
|-------|--------|-------------|
| Minute | 0-59 | Minute of the hour |
| Hour | 0-23 | Hour of the day (24-hour format) |
| Day | 1-31 | Day of the month |
| Month | 1-12 | Month of the year |
| Weekday | 0-6 | Day of week (0=Sunday, 1=Monday, ..., 6=Saturday) |

Common patterns:
- `0 9 * * *` → Every day at 9:00 AM
- `0 9 * * 1-5` → Weekdays at 9:00 AM
- `0 9 * * 0` → Every Sunday at 9:00 AM
- `0 0 1 * *` → First day of each month at midnight
- `*/30 * * * *` → Every 30 minutes

## Example Conversation

**User**: I want to create an automation that generates weekly reports every Monday morning.

**Agent**: I'll help you create that automation. Let's go through the details:

**1. Name**: What would you like to call this automation?

**User**: Weekly Report Generator

**Agent**: **2. Cron Schedule**: You mentioned Monday mornings. What time would you like it to run? (in UTC)

**User**: 9 AM

**Agent**: So `0 9 * * 1` for every Monday at 9:00 AM UTC. 

**3. Tarball Path**: Where is your automation code stored?

**User**: s3://my-bucket/automations/weekly-report.tar.gz

**Agent**: **4. Entrypoint**: What command runs your report generator?

**User**: python generate_report.py

**Agent**: **5. Setup Script** (optional): Do you need a setup script to run first?

**User**: No

**Agent**: **6. Timeout** (optional): How long should it be allowed to run? (max 600 seconds)

**User**: 5 minutes should be enough

**Agent**: Creating your automation with:
- Name: Weekly Report Generator
- Schedule: Every Monday at 9:00 AM UTC
- Code: s3://my-bucket/automations/weekly-report.tar.gz
- Command: python generate_report.py
- Timeout: 300 seconds

[Executes API call]

✅ Automation created successfully!
- **ID**: 550e8400-e29b-41d4-a716-446655440000
- **Name**: Weekly Report Generator
- **Schedule**: Every Monday at 9:00 AM UTC
- **Status**: Enabled

Your automation will run for the first time next Monday at 9:00 AM UTC.
