# Usage And Proof

Use this reference when the reviewer asks:

- what does the skill actually help an agent do?
- how do I try it in a few minutes?
- where is the public proof?

## First-success path

Run the zero-risk path in this order:

```bash
notes-recovery demo
notes-recovery ai-review --demo
notes-recovery ask-case --demo --question "What should I inspect first?"
notes-recovery doctor
```

What this proves:

- the repo already ships a public-safe demo surface
- AI review is real, not hypothetical
- bounded case Q&A is real, not hypothetical
- the MCP lane belongs on one explicit case root

## MCP capability surface after attach

- Read-only review surfaces:
  `list_case_roots`, `inspect_case_manifest`, `select_case_evidence`,
  `inspect_case_artifact`, and `ask_case`
- Bounded workflows:
  `run_verify`, `run_report`, `build_timeline`, and `public_safe_export`
- Boundary:
  local stdio only, one explicit case root at a time, and no live Notes store
  access

## Example prompts

- "Summarize the demo case and list the first two artifacts I should inspect."
- "Use the NoteStore Lab MCP lane on this case root and tell me what proof surfaces are available."
- "Compare case A and case B and focus on the review layer, not raw copied evidence."
- "Generate a safe sharing plan using public-safe export."

## Public proof links

- Landing page: https://xiaojiou176-open.github.io/apple-notes-forensics/
- Public proof page: https://github.com/xiaojiou176-open/apple-notes-forensics/blob/main/proof.html
- Builder guide: https://github.com/xiaojiou176-open/apple-notes-forensics/blob/main/INTEGRATIONS.md
- Distribution boundary: https://github.com/xiaojiou176-open/apple-notes-forensics/blob/main/DISTRIBUTION.md
- Releases: https://github.com/xiaojiou176-open/apple-notes-forensics/releases

## Visual demo

![NoteStore Lab demo screenshot](https://raw.githubusercontent.com/xiaojiou176-open/apple-notes-forensics/main/assets/readme/hero-public-demo.png)

## Reviewer checklist

If a reviewer asks "what does this skill teach?", answer in one sentence:

> It teaches an agent how to install NoteStore Lab's local MCP lane, prove the
> workflow on demo artifacts, and review one copied Apple Notes case root using
> derived artifacts instead of the live Notes store.
