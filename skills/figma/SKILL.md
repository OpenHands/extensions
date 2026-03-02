---
name: figma
description: Access Figma designs using the Figma MCP server. Read design files, extract components, get design tokens, and inspect layer properties.
triggers:
- figma
- figma design
- figma mcp
---

# Figma MCP

Access Figma designs via the official MCP server with OAuth authentication.

## Quick Start

```bash
openhands mcp add figma --transport http --auth oauth https://figma.com/mcp/sse
openhands mcp list  # Verify installation
```

Restart OpenHands after installation. OAuth authorization prompt appears on first use.

## Available Tools

- **get_file** - Read design file structure and metadata
- **get_file_nodes** - Extract specific components/layers
- **get_images** - Export design assets
- **get_comments** - Read design comments
- **get_styles** - Get design tokens (colors, typography, etc.)

## Documentation

- [Figma MCP Server](https://developers.figma.com/docs/figma-mcp-server)
- [Figma API Reference](https://www.figma.com/developers/api)
