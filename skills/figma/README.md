# Figma MCP

Read-only access to Figma designs using the Figma MCP server. Read design files, extract components, get design tokens, and inspect layer properties.

## Overview

The Figma MCP server provides tools to interact with Figma designs directly from OpenHands. It uses OAuth authentication to securely access your Figma account.

With the server enabled, you can:

- **Generate code from selected frames**: Select a Figma frame and turn it into code
- **Extract design context**: Pull in variables, components, and layout data
- **Retrieve design tokens**: Access colors, typography, and spacing values
- **Inspect layer properties**: Get detailed information about any design element

## Installation

```bash
openhands mcp add figma --transport http https://mcp.figma.com/mcp
```

This adds the Figma MCP server to your OpenHands configuration. OAuth authentication is handled automatically by the server - you'll be prompted to authorize via your browser when first accessing Figma data.

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

## Usage

The MCP server is link-based. To use it:

1. Copy the link to a frame or layer in Figma
2. Prompt OpenHands to help you implement the design at the selected URL

The agent will extract the node-id from the URL and retrieve information about that object.

## Troubleshooting

- **OAuth errors**: Re-run the installation command to re-authenticate
- **Server not found**: Ensure you've restarted your OpenHands session after installation
- **Access denied**: Verify you have view access to the Figma file you're trying to access

## Documentation

- [Figma MCP Server](https://developers.figma.com/docs/figma-mcp-server)
- [Remote Server Installation](https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/)
- [Figma API](https://www.figma.com/developers/api)
