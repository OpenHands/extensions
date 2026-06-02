# Automation catalog

This directory contains recommended OpenHands automation templates.

- `catalog/*.json` contains one source file per recommended automation.
- `index.js` assembles and exports the catalog for Node.js and bundlers.
- `index.d.ts` contains the public TypeScript shape.
- `examples/` contains concrete custom-script examples for templates that need deterministic pre-agent work, such as local polling before creating a conversation.

Consumers can import the package export:

```js
import { AUTOMATION_CATALOG } from "@openhands/extensions/automations";
```

Each automation references required integrations by ID. Those IDs should match entries in `integrations/catalog/*.json`.

Polling automations should not use prompt presets for the polling step. Use a custom script that polls first, exits without a conversation when there is no work, and only creates an OpenHands conversation after the script finds an actionable event. See `examples/github-pr-reviewer-polling/` for a complete example.
