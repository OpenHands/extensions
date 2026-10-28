# Conversation Trace

Conversation Trace adds a routed Agent Canvas page for inspecting any conversation on the active Agent Server as a complete chronological event ledger.

The page provides:

- paginated conversation and event history loading;
- message, tool, file, command, approval, error, state, and unknown-event categories;
- a compact chronology overview, metrics, event search, and category filters;
- action/observation duration correlation through tool call IDs;
- an event inspector with focused fields and the complete raw payload;
- automatic refresh for active conversations;
- responsive, keyboard-operable controls and safe text-only rendering.

## Package

This is a dependency-free Canvas Extension targeting manifest schema 1 and host API 1. Its self-contained browser ESM entrypoint is `extension.js`.

## Install

Add this repository in **Customize → Extensions** and use `conversation-trace` as the repository path. Installation leaves the extension disabled. Review it, then enable it to add the **Trace** navigation item.

For a backend-local install, select this directory as the source path on the Agent Server machine.

## Verify

```sh
node /path/to/agent-canvas-extension-builder/scripts/validate-extension.mjs conversation-trace
/path/to/vitest run conversation-trace/extension.test.js --environment jsdom
```

After enabling, open `/extensions/conversation-trace/trace`, select a conversation, exercise event search and filters, inspect an event, and verify active conversations refresh without a page reload.

## Current limitations

Canvas Extension host API 1 exposes authenticated REST requests but no extension WebSocket helper. Conversation Trace therefore polls active histories every five seconds rather than subscribing to live events. The page limits a single rendered trace to 5,000 events to keep browser interaction responsive.
