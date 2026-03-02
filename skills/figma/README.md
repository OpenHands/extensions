# Figma MCP Skill

> See [SKILL.md](./SKILL.md) for the agent-consumable skill definition.

This directory contains the Figma MCP skill for OpenHands.

## Overview

The Figma MCP server provides tools to interact with Figma designs directly from OpenHands using the official [Figma MCP Server](https://developers.figma.com/docs/figma-mcp-server).

## Installation

```bash
openhands mcp add figma --transport http --auth oauth https://figma.com/mcp/sse
```

Restart OpenHands after installation.

## Server Management

```bash
openhands mcp list           # List all MCP servers
openhands mcp get figma      # Get Figma server details
openhands mcp disable figma  # Temporarily disable
openhands mcp enable figma   # Re-enable
openhands mcp remove figma   # Remove completely
```

## Resources

- [Figma MCP Server Documentation](https://developers.figma.com/docs/figma-mcp-server)
- [Remote Server Installation Guide](https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/)
- [Figma REST API Reference](https://www.figma.com/developers/api)
