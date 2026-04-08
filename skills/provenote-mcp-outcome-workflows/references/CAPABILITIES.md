# Provenote MCP Capabilities

These are the MCP tool families this skill expects the host to expose.

## Read-first tool families

- `draft.*`
  - inspect, create, verify, and download notebook drafts
- `research_thread.*`
  - inspect or evolve research threads, then promote one into a draft
- `auditable_run.*`
  - inspect and create auditable output bundles

## Recommended first-use sequence

1. `draft.list`
2. `research_thread.list`
3. `auditable_run.list`

That sequence tells the agent what already exists before it proposes any write
action.

## Good next actions

- `research_thread.to_draft`
- `draft.verify`
- `draft.download`
- `auditable_run.create`
- `auditable_run.download`

## Utility surfaces

- `knowledge.search`
- `chat.run`
- `model.inspect`
- `settings.mutate`

Use these after the read-first workflow is already grounded in the user's
actual drafts or research threads.
