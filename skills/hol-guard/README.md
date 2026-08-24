# HOL Guard

This OpenHands skill provides operational guidance for the real HOL Guard security CLI and its separate plugin scanner.

Use it to:

- install and verify `hol-guard`;
- protect a local AI harness that HOL Guard currently supports;
- review Guard approvals, receipts, and evidence;
- scan agent skills, plugins, MCP server packages, marketplace packages, or mixed workspaces with `plugin-scanner`.

It intentionally does not claim a native OpenHands pre-tool interception hook. For OpenHands workspaces, the skill can run Guard and scanner workflows from the agent environment, while harness protection is limited to targets explicitly supported by HOL Guard.

## Quick start

```bash
pipx install hol-guard
hol-guard status
hol-guard detect --json
```

For package scanning:

```bash
pipx install plugin-scanner
plugin-scanner lint .
plugin-scanner verify .
```

## Sources

- Product: https://hol.org/guard
- Plugin and Agent Skill: https://github.com/hashgraph-online/hol-guard-plugin
- Runtime: https://github.com/hashgraph-online/hol-guard
