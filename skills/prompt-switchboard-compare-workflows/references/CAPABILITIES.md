# Prompt Switchboard MCP Capabilities

These are the MCP tools this skill expects the host to expose.

## Best first tools

- `prompt_switchboard.bridge_status`
  - confirm the local bridge is reachable
- `prompt_switchboard.check_readiness`
  - tell the agent which model tabs are ready before it spends the user's prompt
- `prompt_switchboard.compare`
  - send one prompt across the ready tabs and create an inspectable compare turn

## Useful follow-through tools

- `prompt_switchboard.analyze_compare`
  - summarize the compare turn
- `prompt_switchboard.export_compare`
  - export the compare as Markdown or a compact local share artifact
- `prompt_switchboard.retry_failed`
  - rerun only the failed model tabs

## Workflow tools

- `prompt_switchboard.run_workflow`
- `prompt_switchboard.list_workflow_runs`
- `prompt_switchboard.get_workflow_run`
- `prompt_switchboard.resume_workflow`

These tools are best after one real compare turn already exists.

## Session inspection tools

- `prompt_switchboard.get_session`
- `prompt_switchboard.list_sessions`

Use these when the user wants to inspect or export prior compare history.
