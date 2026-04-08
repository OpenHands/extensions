# Usage And Proof

Use this reference when the reviewer asks what the skill helps an agent do in
practice.

## First-success path

```bash
./notesctl run --no-status
./notesctl install --minutes 30 --load
./notesctl verify
./notesctl doctor
./notesctl status --full
```

Then move into builder surfaces:

```bash
./notesctl ai-diagnose
./notesctl web
./notesctl mcp
```

## Example prompts

- "Is this Apple Notes Snapshot problem a local preflight failure or an MCP attach failure?"
- "Explain the current backup loop status using the control-room proof path."
- "Which surface should I use here: AI Diagnose, Local Web API, or MCP?"

## Public links

- Landing: https://xiaojiou176-open.github.io/apple-notes-snapshot/
- Quickstart: https://xiaojiou176-open.github.io/apple-notes-snapshot/quickstart/
- Proof page: https://xiaojiou176-open.github.io/apple-notes-snapshot/proof/
- MCP guide: https://xiaojiou176-open.github.io/apple-notes-snapshot/mcp/
- For Agents: https://xiaojiou176-open.github.io/apple-notes-snapshot/for-agents/
