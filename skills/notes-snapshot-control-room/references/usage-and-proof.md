# Usage And Proof

Use this reference when the reviewer asks:

- what does the skill help an agent do in practice?
- where is the public proof?
- how do I test it without guessing?

## First-success path

Acquire the tool first if needed:

```bash
git clone --depth 1 --branch v0.1.12 \
  https://github.com/xiaojiou176-open/apple-notes-snapshot.git
cd apple-notes-snapshot
```

Then run the shortest truthful path:

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

## MCP capability surface after attach

- Tools:
  `get_status`, `run_doctor`, `verify_freshness`, `get_log_health`,
  `list_recent_runs`, and `get_access_policy`
- Resource:
  `notes-snapshot://recent-runs`
- Boundary:
  the MCP lane is local stdio, read-only-first, and backed by the same
  repo-owned state as the operator lane

## Example prompts

- "Is this Apple Notes Snapshot problem a local preflight failure or an MCP attach failure?"
- "Explain the current backup loop status using the control-room proof path."
- "Walk me from operator proof to builder attach without overstating what is officially listed."
- "Which surface should I use here: AI Diagnose, Local Web API, or MCP?"

## Proof / demo links

- Landing: https://xiaojiou176-open.github.io/apple-notes-snapshot/
- Quickstart: https://xiaojiou176-open.github.io/apple-notes-snapshot/quickstart/
- Proof page: https://xiaojiou176-open.github.io/apple-notes-snapshot/proof/
- MCP provider guide: https://xiaojiou176-open.github.io/apple-notes-snapshot/mcp/
- For Agents overview: https://xiaojiou176-open.github.io/apple-notes-snapshot/for-agents/
- Public skills pack docs: https://xiaojiou176-open.github.io/apple-notes-snapshot/for-agents/public-skills/

## Visual demo

![Apple Notes Snapshot run flow](https://raw.githubusercontent.com/xiaojiou176-open/apple-notes-snapshot/main/assets/readme/run-flow.gif)

## Reviewer one-liner

If the reviewer asks "what does this skill teach?", answer:

> It teaches an agent how to prove Apple Notes Snapshot's local control room,
> wire the `notesctl mcp` lane, and separate repo proof, host proof, AI
> Diagnose, Local Web API, and MCP into honest boundaries.
