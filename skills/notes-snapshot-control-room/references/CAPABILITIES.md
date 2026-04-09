# Apple Notes Snapshot MCP Capabilities

These are the MCP tools and resources this packet expects the host to expose.

## Safe-first tools

- `get_status`
- `run_doctor`
- `verify_freshness`
- `get_log_health`
- `list_recent_runs`
- `get_access_policy`

## First resource to read back

- `notes-snapshot://recent-runs`

## Best default order

1. `get_status`
2. `verify_freshness`
3. `run_doctor`
4. `list_recent_runs`
5. `get_access_policy`
