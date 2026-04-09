# DealWatch MCP Capabilities

These are the stable read-only tools exposed by the published DealWatch MCP.

## Safe-first tools

1. `get_runtime_readiness`
   - use first when setup, environment, or startup truth is unclear
2. `compare_preview`
   - use first when the user wants to compare candidate grocery URLs without
     creating durable state
3. `get_builder_starter_pack`
   - use when the user needs the integration contract, launch commands, and
     host setup path

## Watch-task tools

- `list_watch_tasks`
- `get_watch_task_detail`

Use these after the safe-first path is already clear.

## Watch-group tools

- `list_watch_groups`
- `get_watch_group_detail`

Use these after the user is already inside an existing watch-group flow.

## Recovery and runtime follow-up

- `get_recovery_inbox`
- `list_notifications`
- `get_notification_settings`
- `list_store_bindings`
- `get_store_onboarding_cockpit`

Use these only after the safe-first path is grounded in a real runtime state.
