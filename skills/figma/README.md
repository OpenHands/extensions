# Figma MCP

Read Figma design data using the Figma MCP server. Inspect files, components, design tokens, and layer properties.

## Overview

The Figma MCP server provides tools to interact with Figma designs directly from OpenHands. It uses OAuth authentication to securely access your Figma account.

With the server enabled, you can:

- **Generate code from frames**: Ask OpenHands to read a Figma frame through MCP and generate React, HTML, or other code from the retrieved design data
- **Extract design context**: Retrieve variables, components, and layout information from a file or frame
- **Retrieve design tokens**: Pull colors, typography, spacing, and other reusable style values
- **Inspect node properties**: Review supported node types such as frames, components, instances, text, and shapes

## Installation

```bash
openhands mcp add figma --transport http https://mcp.figma.com/mcp
```

This adds the Figma MCP server to your OpenHands configuration. The first time OpenHands calls a Figma MCP tool, the server will open your browser and prompt you to authorize access with Figma OAuth.

**Note:** Restart your OpenHands session after installation to load the new MCP server. This is required because MCP servers are initialized at session startup.

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

The MCP server is link-based. Start by copying the link to a Figma file, frame, or layer, then use a prompt like one of these in OpenHands:

- **Generate code from a frame**
  ```text
  Generate a React component from this Figma frame: https://www.figma.com/file/ABC123/MyDesign?node-id=1-2
  ```
- **Extract design tokens from a file**
  ```text
  List the colors, typography, and spacing tokens used in this Figma file: https://www.figma.com/file/ABC123/MyDesign
  ```
- **Inspect component structure**
  ```text
  Show me the component tree and layer hierarchy for this Figma frame: https://www.figma.com/file/ABC123/MyDesign?node-id=1-2
  ```

For each prompt, OpenHands uses the Figma MCP server to read the referenced design data before generating a response.

## Troubleshooting

- **OAuth errors**:
  1. Visit `https://www.figma.com/`, log out, and log back in to refresh your Figma session
  2. If that does not work, clear your browser cookies/cache for `figma.com`
  3. Restart your OpenHands session and retry the same Figma prompt

  Re-running `openhands mcp add` refreshes the server configuration, but it does not reset OAuth state cached in your browser.
- **Server not found**: Ensure you've restarted your OpenHands session after installation
- **Access denied**: Verify you have view access to the Figma file you're trying to access

## Documentation

- [Figma MCP Server](https://developers.figma.com/docs/figma-mcp-server)
- [Remote Server Installation](https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/)
- [Figma API](https://www.figma.com/developers/api)
