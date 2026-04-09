# Usage And Proof

Use this reference when the reviewer asks:

- what does the skill help an agent do in practice?
- where is the public proof?
- how do I test it without guessing?

## First-success path

```bash
./notesctl run --no-status
./notesctl install --minutes 30 --load
./notesctl verify
./notesctl doctor
./notesctl status --full
```

Then, if the local state exists, move into builder surfaces:

```bash
./notesctl ai-diagnose
./notesctl web
./notesctl mcp
```

## Proof / demo links

- Landing: https://xiaojiou176-open.github.io/apple-notes-snapshot/
- Quickstart: https://xiaojiou176-open.github.io/apple-notes-snapshot/quickstart/
- Proof page: https://xiaojiou176-open.github.io/apple-notes-snapshot/proof/
- MCP provider guide: https://xiaojiou176-open.github.io/apple-notes-snapshot/mcp/
- For Agents overview: https://xiaojiou176-open.github.io/apple-notes-snapshot/for-agents/
