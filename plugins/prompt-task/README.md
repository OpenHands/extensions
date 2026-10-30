# prompt-task

The stock plugin behind prompt automations. It turns a typed prompt into a
plugin-spec automation, so the run is launched from the agent profile chosen
for the automation: its tools (including sub-agents), MCP servers, skills and
model.

## Usage

Create the automation through the Automation Service's `POST /v1/plugin-spec`:

```json
{
  "name": "Weekly issue triage",
  "plugin": {
    "source": "github:OpenHands/extensions",
    "repo_path": "plugins/prompt-task"
  },
  "config": {"prompt": "Label every unlabeled issue opened this week"},
  "agent_profile_id": "<agent profile id>",
  "trigger": {"type": "cron", "schedule": "0 9 * * 1", "timezone": "UTC"}
}
```

Each run sends `/prompt-task:run <prompt>`, where `<prompt>` is the
`config.prompt` value, to a conversation the service starts from the agent
profile. The manifest names no default profile, so `agent_profile_id` is
required; a client normally defaults it to the user's active profile.

`agent_profile_id` requires an Automation Service that advertises
`pluginSpecAgentProfiles` in `GET /v1/capabilities`.
