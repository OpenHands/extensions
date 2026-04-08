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

Use this skill when you want OpenHands to inspect one SourceHarbor watchlist and answer a question with the current story and evidence context.

Think of it as an **operator briefing plugin without executable code**:

- it teaches the agent how to use SourceHarbor's MCP or HTTP API
- it starts from one watchlist
- it reuses the current briefing/story payload
- it answers one operator question with evidence
- it finishes with one concrete next action

## What this skill teaches the agent

- how to prefer SourceHarbor MCP when it is already connected
- how to fall back to the HTTP API without pretending the product is hosted SaaS
- how to answer from the current story and change set rather than from vague search alone
- how to return a briefing-style answer with explicit evidence and next action

## Inputs To Fill In

- `WATCHLIST_ID`: the watchlist you want to inspect
- `QUESTION`: the question you want answered
- `SOURCE_HARBOR_API_BASE_URL`: the SourceHarbor API base URL when MCP is not wired
- `SOURCE_HARBOR_MCP_STATUS`: whether SourceHarbor MCP is already connected

## Runtime you need

- a connected SourceHarbor MCP server, or
- a running local SourceHarbor HTTP API
- if neither is ready yet, use `references/mcp-and-http-setup.md`

## Capability map

SourceHarbor exposes a shared operator truth across MCP and HTTP API. The capability groups that matter most for this skill are:

- watchlist and briefing retrieval
- Ask/search over the current story context
- jobs, artifacts, and reports as evidence follow-ups
- health and workflow tools when the runtime itself needs checking

Use `references/capability-map.md` for a concrete tool-group map.

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

Return a compact answer with:

- `current_story`
- `what_changed`
- `evidence_used`
- `suggested_next_action`
- `runtime_gap` if MCP or HTTP access was partial

## Guardrails

- Do not pretend SourceHarbor is a hosted SaaS.
- Do not turn sample or demo surfaces into live-proof claims.
- Do not answer without evidence.
- If MCP or HTTP access is partial, say so clearly instead of filling gaps.

## Local references

- `references/mcp-and-http-setup.md`
- `references/capability-map.md`
- `references/example-output.md`
