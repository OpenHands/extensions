# Install And MCP Wiring

Use this reference when the agent or reviewer asks:

- how do I install this?
- what is the exact MCP command?
- what should I point my host at?

## Public package lane

The current shipped package lane is PyPI:

```bash
python -m pip install apple-notes-forensics==0.1.0.post1
```

If the host supports `uvx`, the shortest MCP launch path is:

```bash
uvx --from apple-notes-forensics==0.1.0.post1 \
  notes-recovery-mcp \
  --case-dir ./output/Notes_Forensics_<run_ts>
```

## Source checkout lane

If the user is working from a cloned repository checkout:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .[mcp]
notes-recovery-mcp --case-dir ./output/Notes_Forensics_<run_ts>
```

## Generic MCP host config

Use this when a host expects a `mcpServers` JSON block:

```json
{
  "mcpServers": {
    "notestorelab": {
      "command": "uvx",
      "args": [
        "--from",
        "apple-notes-forensics==0.1.0.post1",
        "notes-recovery-mcp",
        "--case-dir",
        "./output/Notes_Forensics_<run_ts>"
      ]
    }
  }
}
```

If `uvx` is unavailable, point the host at the repo-local Python command
instead.

## Capability boundary

This MCP surface is:

- local
- stdio-first
- one explicit case root at a time
- read-mostly
- derived-artifact-first

This MCP surface is **not**:

- a hosted Notes service
- a remote multi-tenant API
- a write path into the live Apple Notes store
