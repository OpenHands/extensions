---
name: sourceharbor-watchlist-briefing
description: Use SourceHarbor watchlists, briefings, Ask, MCP, and HTTP API to answer one question with current story context and evidence.
triggers:
  - sourceharbor
  - watchlist
  - briefing
  - operator question
---

# SourceHarbor Watchlist Briefing

Use this skill when you want OpenClaw to inspect one SourceHarbor watchlist and
answer a question with the current story and evidence context.

Think of it as an **operator briefing skill card**:

- it teaches the agent the workflow
- it names the MCP/HTTP setup needed
- it shows which SourceHarbor capabilities matter
- it keeps the answer evidence-backed and operational

## Goal

- start from one watchlist
- reuse the current briefing or story payload
- answer one operator question
- cite the evidence used
- return one concrete next action

## Runtime you need

- one connected SourceHarbor MCP server, or
- one running SourceHarbor HTTP API at `SOURCE_HARBOR_API_BASE_URL`
- if either still needs wiring, use `references/INSTALL.md`

## Exposed MCP abilities

This skill is built around these SourceHarbor capability groups:

- health
- retrieval / Ask-style evidence lookup
- jobs and compare views
- artifacts and reports
- workflows, subscriptions, and notifications when the question is really about operator state

Use `references/CAPABILITIES.md` for the concrete tool map.

## Inputs To Fill In

- `WATCHLIST_ID`: the watchlist you want to inspect
- `QUESTION`: the question you want answered
- `SOURCE_HARBOR_API_BASE_URL`: the SourceHarbor API base URL when MCP is not wired
- `SOURCE_HARBOR_MCP_STATUS`: whether SourceHarbor MCP is already connected

## Workflow

Use the strongest available path in this order:

1. SourceHarbor MCP, if it is already connected
2. SourceHarbor HTTP API at `SOURCE_HARBOR_API_BASE_URL`
3. SourceHarbor web routes only as visible proof surfaces

Required steps:

1. Load the watchlist object.
2. Load the current watchlist briefing or briefing page payload.
3. Identify the selected story and the recent changes.
4. Answer `QUESTION` using that story context.
5. Return:
   - Current story
   - What changed
   - Evidence used
   - Suggested next operator action

## Output contract

Return:

- `current_story`
- `what_changed`
- `evidence_used`
- `suggested_next_action`
- `runtime_gap` if MCP or HTTP access was partial

## Guardrails

- Do not pretend SourceHarbor is a hosted SaaS.
- Do not turn sample/demo surfaces into live-proof claims.
- Do not answer without evidence.
- If MCP or HTTP access is partial, say so clearly instead of filling gaps.

## Companion references

- `README.md`
- `references/README.md`
- `references/INSTALL.md`
- `references/OPENHANDS_MCP_CONFIG.json`
- `references/OPENCLAW_MCP_CONFIG.json`
- `references/CAPABILITIES.md`
- `references/DEMO.md`
- `references/TROUBLESHOOTING.md`
