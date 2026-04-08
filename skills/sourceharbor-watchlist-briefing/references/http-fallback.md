# SourceHarbor HTTP Fallback

Use this path only when SourceHarbor MCP is unavailable and the local HTTP API is already running.

## Required base URL

```bash
export SOURCE_HARBOR_API_BASE_URL=http://127.0.0.1:9000
```

## Most relevant endpoints

1. Get the watchlist object:

```bash
curl -s "$SOURCE_HARBOR_API_BASE_URL/api/v1/watchlists/$WATCHLIST_ID"
```

2. Get the unified briefing payload:

```bash
curl -s "$SOURCE_HARBOR_API_BASE_URL/api/v1/watchlists/$WATCHLIST_ID/briefing"
```

3. If you need the selected-story page payload:

```bash
curl -s "$SOURCE_HARBOR_API_BASE_URL/api/v1/watchlists/$WATCHLIST_ID/briefing/page?story_id=$STORY_ID"
```

## What to extract

- the current story summary
- what changed across the compare window
- cited evidence cards or artifact references
- the next action implied by the current story

If the briefing payload is not enough to answer the question, say so instead of inventing a conclusion.
