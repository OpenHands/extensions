# MCP catalog

This directory contains curated MCP server metadata for OpenHands clients.

- `catalog/*.json` contains one source file per MCP marketplace entry.
- `index.js` assembles and exports the catalog for Node.js and bundlers.
- `index.d.ts` contains the public TypeScript shape.

Consumers can import the package export:

```js
import { MCP_CATALOG } from "@openhands/extensions/mcps";
```

The catalog intentionally stores only serializable data. Client applications are responsible for mapping entries to UI-specific icons or styling.
