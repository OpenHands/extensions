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

## Install in Agent Canvas

In **Customize → Apps → Add app**, paste this folder's URL at the commit you reviewed as **App source**:

```text
https://github.com/OpenHands/extensions/tree/<commit>/apps/usage-insights
```

The form splits it into source `https://github.com/OpenHands/extensions`, **Ref** `<commit>` and **Path** `apps/usage-insights`. The App installs disabled. Review its source at that revision, switch it on and confirm **Enable trusted app**, then open **Usage** from the sidebar. Canvas installs a copy, so after a change use **Update** on its card, or uninstall and reinstall.

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

## Source

Moved from [OpenHands/canvas-apps](https://github.com/OpenHands/canvas-apps/tree/b83068fdce5ec7f85c07b8aefa15d413982059d0/usage-insights) at `b83068fdce5ec7f85c07b8aefa15d413982059d0`, keeping the MIT [LICENSE](LICENSE). Installations made from canvas-apps do not follow this move: uninstall them and install again from this registry.
