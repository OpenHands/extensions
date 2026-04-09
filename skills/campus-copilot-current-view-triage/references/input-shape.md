# Current View Input Shape

Use this when Campus Copilot MCP is not connected and the agent only has a snapshot or current-view export.

## What the triage skill needs

At minimum, the input should expose:

- top Focus Queue items
- recent changes or recent updates
- enough site context to decide which area is most urgent

## Minimal mental model

The exact JSON can vary, but the triage workflow expects something equivalent to:

```json
{
  "generatedAt": "2026-04-08T00:00:00Z",
  "focusQueue": [
    {
      "title": "Homework 1",
      "site": "canvas",
      "priority": "high"
    }
  ],
  "recentChanges": [
    {
      "site": "canvas",
      "summary": "New assignment detected"
    }
  ]
}
```

## If you only have a raw workspace snapshot

Use the smallest helpful transformation first:

- inspect the `*_snapshot_view` MCP tools, or
- ask for a current-view export that already summarizes Focus Queue and recent changes

Do not invent overdue items, grades, or browser/session truth that are not present in the provided input.
