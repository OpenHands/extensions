# Usage Insights

Usage Insights adds a routed Agent Canvas page for tracking OpenHands conversation token usage and estimated cost.

The page provides:

- token consumption (prompt, completion, cache-read, cache-write, reasoning);
- estimated token cost with clear price provenance (reported / catalog estimate / unpriced);
- breakdowns by time, model, and conversation;
- task-budget progress and over-budget warnings;
- conversation detail with token/cost progression from stats snapshots;
- read-only pricing coverage view;
- backend-scoped browser-local cache of normalized telemetry;
- loading, empty, partial-history, stale-cache, and error states;
- responsive, keyboard-operable controls and safe text-only rendering.

## Package

This is a dependency-free Canvas Extension targeting manifest schema 1 and host API 1. Its self-contained browser ESM entrypoint is `extension.js`.

## Install

Add this repository in **Customize → Extensions** and use `usage-insights` as the repository path. Installation leaves the extension disabled. Review it, then enable it to add the **Usage** navigation item.

For a backend-local install, select this directory as the source path on the Agent Server machine.

## Verify

```sh
node /path/to/canvas-extension-api/scripts/validate-extension.mjs usage-insights
npx vitest run usage-insights/extension.test.js --environment jsdom
```

After enabling, open `/extensions/usage-insights/usage`, exercise the overview, filters, conversation detail, and pricing routes, then verify active conversations refresh without a page reload.

## Data sources

- `GET /api/conversations/search` — paginated conversation list with aggregate stats.
- `GET /api/conversations/{id}/events/search` — paginated event history for stats snapshots.
- `ConversationStateUpdateEvent` entries with `key: "stats"` or `key: "full_state"` are normalized to usage samples.
- `GET /api/profiles` — public profile summaries only (name and model identifier).

The App never calls `GET /api/profiles/{profileName}` or `GET /api/llm/provider-connections`, as these may contain credentials.

## Cost provenance

Cost is resolved in this order:

1. **Reported** — server `accumulated_cost` delta (measured, never estimated).
2. **Catalog estimate** — calculated from a bundled public price catalog matching exact provider/model identity.
3. **Unpriced** — tokens shown without monetary total.

Reasoning tokens are treated as part of completion tokens by default to avoid double counting.

## Current limitations

- History is bounded to 500 conversations and 2,000 stats events per conversation.
- Canvas Extension host API 1 exposes no WebSocket helper; active conversations are polled every 10 seconds.
- The bundled catalog is a small subset of public model prices; models without a catalog match are shown as unpriced.
