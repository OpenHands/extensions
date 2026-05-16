# Automation catalog

This directory contains recommended OpenHands automation templates.

- `catalog.json` is the source of truth for recommended automations.
- `index.js` exports the catalog for Node.js and bundlers.
- `index.d.ts` contains the public TypeScript shape.

Consumers can import the package export:

```js
import { AUTOMATION_CATALOG } from "@openhands/extensions/automations";
```

Each automation references required MCPs by ID. Those IDs should match entries in `mcps/catalog.json`.
