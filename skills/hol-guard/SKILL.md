---
name: hol-guard
description: Use HOL Guard to protect supported local AI harnesses, review Guard approvals and receipts, and scan agent plugins, skills, MCP servers, and marketplace packages before use.
triggers:
- hol guard
- hol-guard
- plugin scanner
- plugin-scanner
- ai security
---

# HOL Guard

HOL Guard is a local security layer for AI tooling. In OpenHands, use this skill to install and operate the actual `hol-guard` and `plugin-scanner` CLIs. This skill does not add an OpenHands pre-tool interception hook. Do not claim OpenHands itself is protected unless HOL Guard explicitly supports that harness and a Guard command proves the protection state.

## Safety rules

- Never read `.env` files.
- Never bypass a HOL Guard approval or silently convert a review decision into an allow.
- Prefer Guard-owned setup and inspection commands over manual edits to another harness's configuration.
- Treat scanner errors as failures until they are inspected.
- Preserve existing user changes and inspect `git status --short` before editing a repository.
- Do not claim protection, approval, or release readiness without command output proving it.

## Install and verify

Install the runtime in an isolated environment when possible:

```bash
pipx install hol-guard
hol-guard status
hol-guard detect --json
```

The scanner is a separate distribution. Install it only when scanning is requested:

```bash
pipx install plugin-scanner
plugin-scanner verify . --json
```

If `pipx` is unavailable, explain that an isolated CLI install is preferred instead of silently modifying the user's Python environment.

## Protect a supported local harness

HOL Guard currently supports these harness identifiers: `codex`, `claude-code`, `copilot`, `cursor`, `gemini`, `hermes`, `openclaw`, `opencode`, and `antigravity`.

For a supported target:

```bash
hol-guard bootstrap
hol-guard install <harness>
hol-guard run <harness> --dry-run
hol-guard run <harness>
hol-guard status
```

Do not substitute `openhands` for `<harness>`. OpenHands is not currently a documented HOL Guard harness target. This registry skill makes the Guard CLI available as an operational security workflow; it does not create a native OpenHands execution gate.

## Review approvals and evidence

When Guard queues work for review, inspect the request before any decision:

```bash
hol-guard approvals
hol-guard approvals open
hol-guard receipts
hol-guard diff <harness>
```

Only approve or deny when the user has explicitly asked for that action after the risk and requested scope are understood.

For audit or handoff evidence:

```bash
hol-guard inventory
hol-guard abom --format json
hol-guard events
hol-guard explain <artifact-id>
```

## Scan an agent package or workspace

Use `plugin-scanner` for skills, plugins, MCP server packages, marketplace packages, and mixed agent workspaces:

```bash
plugin-scanner lint .
plugin-scanner verify .
```

For a specific package:

```bash
plugin-scanner lint <path>
plugin-scanner verify <path>
```

Scan the repository or package root that contains the relevant `SKILL.md`, MCP configuration, plugin manifest, or marketplace metadata. Scanning is inspection, not proof that a runtime harness is protected.

## Report results

Summarize the exact command that ran, what Guard or the scanner found, what remains blocked or risky, and the next user action if one is required. Keep product claims tied to observed command output.

Upstream sources:

- HOL Guard product: https://hol.org/guard
- HOL Guard plugin and skill: https://github.com/hashgraph-online/hol-guard-plugin
- HOL Guard runtime: https://github.com/hashgraph-online/hol-guard
