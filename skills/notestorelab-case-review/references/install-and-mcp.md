# Install And MCP Wiring

Use this reference when the user asks how to install or connect NoteStore Lab
to an MCP-aware host.

## Public package lane

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

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .[mcp]
notes-recovery-mcp --case-dir ./output/Notes_Forensics_<run_ts>
```

## Generic MCP host config

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

## Capability boundary

This MCP surface is local, stdio-first, one-case-root-at-a-time, and
read-mostly. It is not a hosted Notes service or a write path into the live
Notes store.
