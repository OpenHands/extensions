# Automation Creation Plugin

Interactive slash command for creating OpenHands automations via guided prompts.

## Quick Start

```
/automation:create
```

The agent guides you through:
1. Uploading your code as a tarball (if needed)
2. Setting a name, cron schedule, and entrypoint
3. Creating the automation via the OpenHands Cloud API

## Plugin vs Skill

This **plugin** provides the `/automation:create` slash command for interactive automation setup.

For comprehensive API documentation (all endpoints, SDK examples, validation rules), see the **[automation skill](../../skills/automation/SKILL.md)**.

## Plugin Structure

```
automation-creation/
├── .claude-plugin/
│   └── plugin.json      # Plugin manifest
├── commands/
│   └── create.md        # Slash command definition
└── README.md            # This file
```

## Related Resources

- **[Automation Skill](../../skills/automation/SKILL.md)** - Full API reference and SDK examples
- [OpenHands SDK Documentation](https://docs.openhands.dev/sdk)
- [OpenHands Cloud](https://app.all-hands.dev)
- [Cron Expression Reference](https://crontab.guru/)
