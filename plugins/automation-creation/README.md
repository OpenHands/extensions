# Automation Creation Plugin

Interactive slash command for creating OpenHands automations via a guided prompt-based workflow.

## Quick Start

```
/automation:create
```

The agent guides you through:
1. Describing what the automation should do (used as the prompt)
2. Setting a name, cron schedule, and timezone
3. Creating the automation via the preset/prompt API endpoint

The preset endpoint handles all SDK code generation, tarball packaging, and upload automatically.

## Plugin vs Skill

This **plugin** provides the `/automation:create` slash command for interactive automation setup.

For comprehensive API documentation (all endpoints, behavior rules, examples), see the **[OpenHands plugin](../openhands/references/automations.md)**.

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

- **[Automations Reference](../openhands/references/automations.md)** — Full API reference, agent behavior rules, and examples
- **[Custom Automation Reference](../openhands/references/custom-automation.md)** — For advanced users who need custom SDK scripts
- [OpenHands SDK Documentation](https://docs.openhands.dev/sdk)
- [OpenHands Cloud](https://app.all-hands.dev)
- [Cron Expression Reference](https://crontab.guru/)
