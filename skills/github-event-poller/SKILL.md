---
name: github-event-poller
description: This skill should be used when the user wants to create an OpenHands automation that polls a GitHub repository for new events on a schedule (e.g. "watch a repo for new issues / PRs / releases / comments", "poll GitHub for events", "set up a recurring GitHub activity check"). It scaffolds and registers a cron-triggered OpenHands automation that reads the GitHub Events / REST API (preferring a GitHub MCP server if configured, falling back to a `GITHUB_TOKEN` env var) and runs user-defined handler instructions against each new event.
triggers:
  - poll github
  - poll a github repo
  - poll repo events
  - poll repository events
  - github event poller
  - github events automation
  - github activity automation
  - watch github repo
  - watch a github repository
  - monitor github repo
  - monitor a github repository
  - github polling
  - schedule github poll
  - cron github
  - github cron job
---

# GitHub Event Poller

Creates a **cron-triggered OpenHands automation** that periodically polls a GitHub repository for new events and runs user-defined handler instructions on them.

This is different from the built-in GitHub *webhook* trigger:

| Capability             | Webhook trigger (`source: github`)              | This skill (cron + REST polling)            |
| ---------------------- | ----------------------------------------------- | ------------------------------------------- |
| Needs webhook access   | Yes (must own the repo / org or App install)    | **No** — any repo readable by your token    |
| Latency                | Real-time                                       | As frequent as your cron (e.g. every 5 min) |
| Public-repo monitoring | Hard (you don't own webhook config)             | **Easy** — just read public events          |
| State / deduplication  | Handled by webhook delivery                     | Lookback window (managed by this skill)     |

Use this skill when the user **doesn't own** the target repo's webhook config, or when they explicitly want a polling model.

## Prerequisites — confirm before creating

Before calling the API, verify each of these. If anything is missing, ask the user.

1. **Target repo** — `owner/repo` (e.g. `OpenHands/OpenHands`).
2. **Event types of interest** — any combination of:
   `issues`, `pull_request`, `issue_comment`, `pull_request_review`, `pull_request_review_comment`, `push`, `release`, `create`, `delete`, `fork`, `watch`, `member`, `public`.
   GitHub's `/repos/{owner}/{repo}/events` returns these via the unified Events API.
3. **Cron schedule** — default `*/15 * * * *` (every 15 minutes). Don't go below 5 minutes against the GitHub API.
4. **Handler instructions** — natural-language description of what to do for each new event. Should be parameterizable by event type if needed.
5. **Auth strategy for the automation sandbox**:
   - **Preferred:** a GitHub MCP server is configured in the user's OpenHands Cloud account. Check by asking the user (or with the API listed below). The automation's runtime prompt instructs the agent to *prefer MCP tools* when present.
   - **Fallback:** the automation sandbox has a `GITHUB_TOKEN` secret. The runtime prompt falls back to `curl https://api.github.com/...` with that token.
   - At least one of these **must** be available, or the automation will be unable to read GitHub. If neither is present, tell the user and stop — do not create the automation.

### Checking for a configured GitHub MCP server

Ask the user, or inspect their account settings via the OpenHands API (host comes from `<HOST>` if provided, else `https://app.all-hands.dev`):

```bash
curl -s "${OPENHANDS_HOST}/api/conversations/settings" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get("mcp_config",{}),indent=2))'
```

Look for an entry whose name or `command`/`url` references `github`, `mcp-github`, or `github-mcp-server`. If none, fall back to `GITHUB_TOKEN`.

### Checking that GITHUB_TOKEN is available

```bash
curl -s "${OPENHANDS_HOST}/api/automation/v1" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" | head -c 200 >/dev/null  # smoke-test API key
```

`GITHUB_TOKEN` is an OpenHands Cloud secret and is injected automatically into automation sandboxes when registered. If the user isn't sure, have them add it under **Settings → Secrets**.

## How to create the automation

Always use the **prompt preset** (`POST /api/automation/v1/preset/prompt`). Never write a custom SDK script for this skill.

The body has three parameterised pieces:

1. **Cron trigger** — `trigger.schedule`, `trigger.timezone`.
2. **Repos** — clone the target repo into the sandbox so its skills (`AGENTS.md`, etc.) are auto-loaded and the agent can run repo-aware actions.
3. **Prompt** — built from the template in `references/runtime-prompt-template.md`. Substitute these placeholders:
   - `{{OWNER_REPO}}` — e.g. `OpenHands/OpenHands`
   - `{{EVENT_TYPES}}` — JSON array of event types
   - `{{LOOKBACK_MINUTES}}` — typically `cron_interval_minutes * 2` (safety overlap)
   - `{{HANDLER_INSTRUCTIONS}}` — user-supplied instructions block
   - `{{MAX_EVENTS}}` — cap (default `50`) so runs stay bounded

### One-shot create (recommended)

The bundled script `scripts/create_poller.sh` does the substitution and POSTs in one step:

```bash
.agents/skills/github-event-poller/scripts/create_poller.sh \
  --repo OpenHands/OpenHands \
  --events "issues,pull_request,release" \
  --schedule "*/15 * * * *" \
  --name "OpenHands repo activity watcher" \
  --handler "For each new issue or PR, summarise it in 1 sentence and print it. For each release, print version + URL." \
  --host "${OPENHANDS_HOST:-https://app.all-hands.dev}"
```

Required env: `OPENHANDS_API_KEY` (or the local `$OPENHANDS_AUTOMATION_API_KEY` for the in-sandbox automation service — see "Local dev stack" below).

The script prints the new automation's `id` on success.

### Manual create (when the script can't be used)

```bash
PROMPT=$(sed \
  -e 's|{{OWNER_REPO}}|OpenHands/OpenHands|g' \
  -e 's|{{EVENT_TYPES}}|["issues","pull_request","release"]|g' \
  -e 's|{{LOOKBACK_MINUTES}}|30|g' \
  -e 's|{{MAX_EVENTS}}|50|g' \
  -e 's|{{HANDLER_INSTRUCTIONS}}|For each new issue or PR, summarise it in one sentence.|g' \
  .agents/skills/github-event-poller/references/runtime-prompt-template.md)

jq -n --arg name "OpenHands repo activity watcher" --arg prompt "$PROMPT" '{
  name: $name,
  prompt: $prompt,
  trigger: {type:"cron", schedule:"*/15 * * * *", timezone:"UTC"},
  timeout: 600,
  repos: [{url: "https://github.com/OpenHands/OpenHands", ref: "main"}]
}' | curl -s -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/prompt" \
       -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
       -H "Content-Type: application/json" \
       --data @-
```

## After creating

1. **Verify** the automation appears in `GET /api/automation/v1`.
2. **Dispatch once** to confirm it runs end-to-end:
   `POST /api/automation/v1/{id}/dispatch`.
3. **Inspect a run** with `GET /api/automation/v1/{id}/runs?limit=5` and look for `status: COMPLETED`.
4. Show the user the automation `id`, the chosen schedule, and a link to the run in the UI.

## Local dev stack (this sandbox)

If `$OPENHANDS_AUTOMATION_API_KEY` is set, the automation backend is running locally at
`http://host.docker.internal:18001`. Use:

- `Host`: `http://host.docker.internal:18001`
- `Auth header`: `Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY`
  (the `/v1` routes on the local stack do **not** accept `X-API-Key` — only Bearer)

The OpenAPI spec is at `${HOST}/api/automation/openapi.json`. This is useful for testing the skill end-to-end without touching production OpenHands Cloud.

## Files in this skill

- `SKILL.md` — this file. The decision flow / API recipe.
- `references/runtime-prompt-template.md` — the prompt that the **automation's sandbox agent** runs every cron tick. Contains the MCP-vs-token decision logic and the polling/dedup loop.
- `scripts/create_poller.sh` — one-shot wrapper that substitutes the template, builds the JSON body and POSTs it to the preset endpoint.

## Tips & gotchas

- **Rate limits.** Unauthenticated GitHub API = 60 req/h. Authenticated = 5,000 req/h. Always run through MCP or `GITHUB_TOKEN`.
- **Events API window.** `/repos/{owner}/{repo}/events` returns up to ~300 events over ~90 days and is cached for ~60 s. Schedules tighter than 1 min are wasteful.
- **Deduplication.** Polling can re-see the same event when runs overlap. The runtime prompt filters events to `created_at >= now - LOOKBACK_MINUTES`; if you need stronger dedup, instruct the handler to check whether it has already acted (e.g. "before commenting on a PR, search for an existing comment authored by you").
- **Push events** can be huge. If watching `push`, cap the handler with `MAX_EVENTS` and consider filtering to a specific branch in the handler instructions.
- **Don't include secrets in the prompt.** The runtime prompt references `$GITHUB_TOKEN`, which is resolved inside the sandbox — never inline the token value into the automation prompt or JSON body.
