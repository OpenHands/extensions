# Hello World Automation Plugin

This is a minimal plugin-backed **executable** automation. It uses the `script`
runner: the plugin ships a small Python entrypoint (`scripts/main.py`) that the
automation service packages and runs inside the sandbox on every trigger. The
entrypoint reads the resolved plugin config, prints a greeting, and fires the
completion callback.

The automation metadata is embedded in `.plugin/plugin.json` under the
`automation` key:

```json
"automation": {
  "schema_version": "openhands.automation.plugin.v1",
  "entrypoint": {
    "runner": "script",
    "command": "python3 scripts/main.py"
  },
  "suggested_trigger": {
    "type": "cron",
    "schedule": "0 9 * * *",
    "timezone": "UTC"
  }
}
```

At run time, the automation service reads the embedded automation metadata,
packages the script-runner tarball (config, execution metadata, plugin list),
and the agent server runs `scripts/main.py` with `AUTOMATION_PLUGIN_ROOT`
pointing at the fetched plugin root.

### Why the `script` runner?

A `conversation` runner entrypoint requires a pre-provisioned
`runtime.agent_profile` (a named agent profile that must already exist in the
caller's org, and — if `allowed_tools` is set — must enable exactly those
tools). That makes a conversation-runner example impossible to create on a
fresh org without first provisioning the named profile, so a `curl` against
`POST /api/automation/v1/plugin-spec` fails with `422 Agent profile
'hello-world-agent' not found`.

The `script` runner needs no agent profile at all — it runs a deterministic
entrypoint with no conversation and no LLM. That keeps the example
self-contained: the plugin-spec `curl` succeeds and a dispatched run produces
output out of the box. See `scripts/main.py` for the entrypoint.
