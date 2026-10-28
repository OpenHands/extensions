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

## Install in Agent Canvas

In **Customize → Apps → Add app**, paste this folder's URL at the commit you reviewed as **App source**:

```text
https://github.com/OpenHands/extensions/tree/<commit>/apps/conversation-trace
```

The form splits it into source `https://github.com/OpenHands/extensions`, **Ref** `<commit>` and **Path** `apps/conversation-trace`. The App installs disabled. Review its source at that revision, switch it on and confirm **Enable trusted app**, then open **Trace** from the sidebar. Canvas installs a copy, so after a change use **Update** on its card, or uninstall and reinstall.

## Verify

```sh
node /path/to/agent-canvas-extension-builder/scripts/validate-extension.mjs conversation-trace
/path/to/vitest run conversation-trace/extension.test.js --environment jsdom
```

After enabling, open `/extensions/conversation-trace/trace`, select a conversation, exercise event search and filters, inspect an event, and verify active conversations refresh without a page reload.

## Current limitations

Canvas Extension host API 1 exposes authenticated REST requests but no extension WebSocket helper. Conversation Trace therefore polls active histories every five seconds rather than subscribing to live events. The page limits a single rendered trace to 5,000 events to keep browser interaction responsive.

## Source

Moved from [OpenHands/canvas-apps](https://github.com/OpenHands/canvas-apps/tree/b83068fdce5ec7f85c07b8aefa15d413982059d0/conversation-trace) at `b83068fdce5ec7f85c07b8aefa15d413982059d0`, keeping the MIT [LICENSE](LICENSE). Installations made from canvas-apps do not follow this move: uninstall them and install again from this registry.
