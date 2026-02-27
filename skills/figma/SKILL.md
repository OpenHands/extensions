---
name: figma
description: Access Figma designs using the Figma MCP server. Read design files, extract components, get design tokens, and inspect layer properties.
triggers:
- figma
- figma design
- figma mcp
---

# Figma MCP

The Figma MCP server provides tools to interact with Figma designs directly from OpenHands. It uses OAuth authentication to securely access your Figma account.

## Installation

To install the Figma MCP server, run the following command in your terminal:

```bash
openhands mcp add figma --transport http --auth oauth https://figma.com/mcp/sse
```

This will:
1. Add the Figma MCP server to your OpenHands configuration
2. Configure OAuth authentication (you'll be prompted to authorize when first used)
3. Enable the server immediately

After installation, restart your OpenHands session to apply the changes.

## Verification

To verify the installation:

```bash
openhands mcp list
```

You should see the Figma server listed with status "enabled".

## Managing the Server

```bash
# Disable the Figma MCP server
openhands mcp disable figma

# Re-enable the Figma MCP server
openhands mcp enable figma

# Remove the Figma MCP server
openhands mcp remove figma

# Get details about the Figma server
openhands mcp get figma
```

## Documentation

- Figma MCP Server: https://developers.figma.com/docs/figma-mcp-server
- Remote Server Installation: https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/
- Figma API: https://www.figma.com/developers/api
