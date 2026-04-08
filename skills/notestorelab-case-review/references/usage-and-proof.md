# Usage And Proof

Use this reference when a reviewer asks what the skill helps an agent do in
practice.

## First-success path

```bash
notes-recovery demo
notes-recovery ai-review --demo
notes-recovery ask-case --demo --question "What should I inspect first?"
notes-recovery doctor
```

What this proves:

- the repo already ships a public-safe demo surface
- AI review is real
- bounded case Q&A is real
- the MCP lane belongs on one explicit case root

## Example prompts

- "Summarize the demo case and list the first two artifacts I should inspect."
- "Use the NoteStore Lab MCP lane on this case root and tell me what proof surfaces are available."
- "Compare case A and case B and focus on the review layer, not raw copied evidence."

## Public links

- Landing: https://xiaojiou176-open.github.io/apple-notes-forensics/
- Public proof: https://github.com/xiaojiou176-open/apple-notes-forensics/blob/main/proof.html
- Builder guide: https://github.com/xiaojiou176-open/apple-notes-forensics/blob/main/INTEGRATIONS.md
- Releases: https://github.com/xiaojiou176-open/apple-notes-forensics/releases
