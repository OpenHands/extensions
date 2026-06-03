---
name: research-brief
description: >
  Create an automation that writes a recurring research brief. Uses Tavily
  MCP for web research and Notion MCP to publish the final brief with
  executive summary, implications, and source citations.
triggers:
  - /research-brief:setup
---

# Research Brief Writer Automation

Set up a recurring automation that researches a topic and publishes a brief
to Notion.

---

## Prerequisites

### Required integrations

Both MCP integrations must be installed in Settings → MCP:

- **Tavily MCP** — for web research and source gathering
- **Notion MCP** — to publish the research brief

### Information to collect

Ask the user for:

1. **Topic** — what should be researched (e.g. "AI code review tools", "competitor pricing changes")
2. **Keywords and competitors** — specific terms, companies, or products to track
3. **Source quality rules** — any preferences on source types (e.g. prefer academic papers, exclude social media)
4. **Cadence** — how often should the brief run? (daily, weekly, bi-weekly)
5. **Notion destination** — which Notion database or page should receive the brief
6. **Citation style** — inline links, footnotes, or a references section
7. **Brief structure** — default: Executive Summary, Key Findings, Implications, Recommended Actions, Sources

---

## Setup Workflow

### Step 1 — Verify MCP access

Test each integration:
```
Use the Tavily MCP to search for a sample topic.
Use the Notion MCP to search for the destination database.
```

If any fail, tell the user which integration needs to be installed first.

### Step 2 — Configure the schedule

Based on the user's cadence preference, build a cron schedule:
- Daily: `0 8 * * 1-5` (weekday mornings)
- Weekly: `0 9 * * 1` (Monday morning)
- Bi-weekly: `0 9 1,15 * *` (1st and 15th)

Ask for timezone preference.

### Step 3 — Build the research prompt

Construct a prompt that includes:
- Research topic and keywords
- Competitor/entity tracking list
- Source quality preferences
- Brief structure template
- Notion destination details
- Citation format

### Step 4 — Create the automation

Read the Automation backend URL and auth from `<RUNTIME_SERVICES>`:
- Use the **Automation backend** `url_from_agent` as `OPENHANDS_HOST`
- Auth: `X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY`

Use the **prompt preset** endpoint:
```bash
curl -s -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/prompt" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Research Brief Writer",
    "prompt": "<constructed research prompt>",
    "trigger": {"type": "cron", "schedule": "<schedule>", "timezone": "<tz>"}
  }'
```

### Step 5 — Confirm

Tell the user:
> ✅ **Research Brief Writer** is running!
>
> - Automation ID: `{id}`
> - Topic: `{topic}`
> - Schedule: `{cron description}`
> - Notion destination: `{destination}`
> - Citation style: `{style}`
