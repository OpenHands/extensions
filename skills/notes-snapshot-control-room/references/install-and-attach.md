# Install And Attach

Use this reference when the user asks how to install or connect Apple Notes
Snapshot to an MCP-aware host.

## Get `notesctl` first

If the host does not already have a checkout with `notesctl`, start from a
public repo checkout:

```bash
git clone --depth 1 --branch v0.1.12 \
  https://github.com/xiaojiou176-open/apple-notes-snapshot.git
cd apple-notes-snapshot
```

If you want current-main behavior instead of the last tagged proof baseline,
clone without `--branch v0.1.12`.

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

Replace `/absolute/path/to/notesctl` with the path from the checkout you just
created, for example `/path/to/apple-notes-snapshot/notesctl`.

## Builder surfaces this skill teaches

- AI Diagnose: `./notesctl ai-diagnose`
- Local Web API: `./notesctl web`
- MCP Provider: `./notesctl mcp`

## MCP capability surface after attach

- `get_status`
- `run_doctor`
- `verify_freshness`
- `get_log_health`
- `list_recent_runs`
- `get_access_policy`
- `notes-snapshot://recent-runs`
