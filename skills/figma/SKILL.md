---
name: figma
description: Read Figma design data using the Figma MCP server. Inspect files, components, design tokens, and layer properties.
triggers:
- figma
- figma design
- figma mcp
---

# Figma MCP

Read Figma design data via the official Figma MCP server. Uses OAuth authentication.

## Installation

```bash
openhands mcp add figma --transport http https://mcp.figma.com/mcp
```

You'll be prompted to authorize via Figma OAuth the first time OpenHands calls a Figma tool. Restart your OpenHands session after installation.

See [README.md](./README.md) for verification, example prompts, management commands, and detailed documentation.
