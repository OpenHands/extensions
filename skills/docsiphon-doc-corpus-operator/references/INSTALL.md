# Install

Docsiphon currently ships through the CLI-first path.

## Fastest path

1. install `uv`
2. run Docsiphon directly from GitHub with `uvx`

```bash
uvx --from git+https://github.com/xiaojiou176-open/docsiphon.git \
  docsiphon --help
```

If you already have a local checkout, you can also install the repo locally:

```bash
uv sync --group dev
uv run docsiphon --help
```

## What this install does not mean

- it does not create a hosted service
- it does not create a browser automation workflow
- it does not mean a current MCP-aware surface is live
