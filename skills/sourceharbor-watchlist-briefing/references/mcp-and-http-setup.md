# SourceHarbor MCP And HTTP Setup

Use this when the host runtime does not already have SourceHarbor connected.

## Local repo setup

1. Clone the public repo:

```bash
git clone https://github.com/xiaojiou176-open/sourceharbor.git
cd sourceharbor
```

2. Start the local MCP surface:

```bash
./bin/dev-mcp
```

3. If you need the HTTP API fallback, make sure the local API is running and set:

```bash
export SOURCE_HARBOR_API_BASE_URL=http://127.0.0.1:9000
```

## What the operator should hand back

- whether SourceHarbor MCP is already connected
- the watchlist id to inspect
- the operator question
- the current `SOURCE_HARBOR_API_BASE_URL` if MCP is not available
