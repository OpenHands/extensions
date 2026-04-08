# Install And Attach

Use this reference when the user asks how to install or connect Apple Notes
Snapshot to an MCP-aware host.

## Minimum operator proof

```bash
./notesctl run --no-status
./notesctl install --minutes 30 --load
./notesctl verify
./notesctl doctor
```

If those commands fail, call it a local snapshot preflight problem, not an MCP
bug.

## MCP launch contract

```bash
./notesctl mcp
```

Generic host config:

```json
{
  "mcpServers": {
    "apple-notes-snapshot": {
      "command": "/absolute/path/to/notesctl",
      "args": ["mcp"]
    }
  }
}
```

## Builder surfaces this skill teaches

- AI Diagnose: `./notesctl ai-diagnose`
- Local Web API: `./notesctl web`
- MCP Provider: `./notesctl mcp`
