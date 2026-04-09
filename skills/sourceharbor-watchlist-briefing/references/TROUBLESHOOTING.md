# SourceHarbor Troubleshooting

Use this page when the packet looks right on paper but the first watchlist
briefing still fails.

## 1. MCP is unavailable

Use the HTTP fallback path from `INSTALL.md` and make the runtime gap explicit.
Do not pretend MCP was connected.

## 2. The HTTP API fallback is unavailable

Check these first:

- the local API is running
- `SOURCE_HARBOR_API_BASE_URL` points at the right base URL
- the watchlist id is valid

If the briefing payload still does not load, report the exact missing endpoint
instead of inventing a story summary.

## 3. The operator question needs more than the current briefing

Escalate narrowly:

1. retrieval / ask-style evidence lookup
2. jobs or compare view only if needed
3. artifacts only if needed

Do not widen into unrelated subscription or notification changes.
