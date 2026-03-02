---
name: figma
description: Read-only access to Figma designs using the Figma MCP server. Read design files, extract components, get design tokens, and inspect layer properties.
triggers:
- figma
- figma design
- figma mcp
---

# Figma MCP

Read-only access to Figma designs via the official Figma MCP server. Uses OAuth authentication.

## Installation

```bash
openhands mcp add figma --transport http https://mcp.figma.com/mcp
```

You'll be prompted to authorize via Figma OAuth when first used. Restart your OpenHands session after installation.

See [README.md](./README.md) for verification, management commands, and detailed documentation.
