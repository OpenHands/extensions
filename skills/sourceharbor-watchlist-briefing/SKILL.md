---
name: sourceharbor-watchlist-briefing
description: Use SourceHarbor watchlists, briefings, Ask, MCP, and HTTP API to answer one question with current story context and evidence.
---

Use this skill when you want OpenHands to inspect one SourceHarbor watchlist and answer a question with the current story and evidence context.

## Goal

- start from one watchlist
- reuse the current briefing or story payload
- answer one operator question
- cite the evidence used
- return one concrete next action

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

## Guardrails

- Do not pretend SourceHarbor is a hosted SaaS.
- Do not turn sample or demo surfaces into live-proof claims.
- Do not answer without evidence.
- If MCP or HTTP access is partial, say so clearly instead of filling gaps.

## Related Public Surfaces

- `docs/compat/openclaw.md`
- `docs/builders.md`
- `docs/mcp-quickstart.md`
- `starter-packs/openclaw/README.md`
