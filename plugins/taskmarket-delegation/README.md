# Taskmarket Delegation Plugin

This OpenHands plugin adds a small MCP bridge for the [Taskmarket](https://taskmarket.dev/) worker market.

## What it provides

- Read-only browsing of public tasks and task status.
- A preparation step that validates a description, duration, mode, visibility, and reward ceiling.
- A create step that requires a one-time preparation token plus the exact confirmation `CREATE_TASK`.
- Submission retrieval for human review; the plugin never accepts or rejects work automatically.

Paid writes are delegated to the first-party `taskmarket` CLI. The bridge does not handle private keys, seed phrases, or payment signatures. Install and configure the CLI separately, then load the plugin with the OpenHands SDK or Cloud:

```python
from openhands.sdk.plugin import PluginSource

plugin = PluginSource(
    source="github:OpenHands/extensions",
    ref="main",
    repo_path="plugins/taskmarket-delegation",
)
```

The MCP server uses `TASKMARKET_API_URL` when set, otherwise `https://api.taskmarket.dev`. The default maximum task reward is 100 USDC and can be lowered with `TASKMARKET_MAX_REWARD_USDC`. The server only invokes `taskmarket task create` after the user has been shown the prepared summary and explicitly confirmed it.

## Safety and review flow

`/taskmarket:delegate` is the user-facing command. Agents should call `taskmarket_prepare_task`, show the returned summary, and wait for an explicit confirmation before calling `taskmarket_create_task`. `taskmarket_list_submissions` is intentionally read-only so a human decides which work to accept.

The MCP bridge is dependency-free and speaks the standard stdio transport. Its tests exercise the protocol, validation, reward ceiling, one-time authorization token, and the no-auto-accept behavior.
