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

3. Before loading the host config snippets in this folder, replace
   `/ABSOLUTE/PATH/TO/sourceharbor` with the real path to your local clone.

4. If you need the HTTP API fallback, make sure the local API is running and set:

```bash
export SOURCE_HARBOR_API_BASE_URL=http://127.0.0.1:9000
```
