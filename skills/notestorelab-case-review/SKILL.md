---
name: notestorelab-case-review
description: This skill should be used when the user asks to "review an Apple Notes case root", "set up NoteStore Lab MCP", "run notes-recovery-mcp", "ask one bounded question about a case", or "compare two NoteStore Lab case roots". It teaches install, first-success proof, and bounded case review without turning the repo into a hosted platform.
triggers:
  - apple notes recovery
  - notes-recovery-mcp
  - review_index
  - ask-case
  - case-diff
---

# NoteStore Lab Case Review

Use this skill when an agent needs to install, wire, or operate the NoteStore
Lab review flow on one explicit case root or the public-safe demo surface.

## What this skill teaches

- how to prove the workflow shape on demo artifacts first
- how to wire the local stdio MCP surface without pretending there is a hosted
  service
- how to inspect one case root at a time using derived artifacts first
- how to ask bounded, evidence-backed questions instead of free-form guessing

## MCP capability surface

- read-only review surfaces: `list_case_roots`, `inspect_case_manifest`,
  `select_case_evidence`, `inspect_case_artifact`, and `ask_case`
- bounded workflows: `run_verify`, `run_report`, `build_timeline`, and
  `public_safe_export`
- one explicit case root at a time, local stdio only, with no live Notes store
  access

## Product truth

- Recovery is the main product.
- AI and MCP are review layers, not the recovery engine.
- Stay local, copy-first, and case-root-driven.
- Prefer derived artifacts before raw copied evidence.
- Do not treat the live Notes store as a target.
- Do not describe NoteStore Lab as a hosted or multi-tenant platform.

## First-success flow

1. Install or launch the shipped surface using `references/INSTALL.md`.
2. Run the public-safe proof path:
   - `notes-recovery demo`
   - `notes-recovery ai-review --demo`
   - `notes-recovery ask-case --demo --question "What should I inspect first?"`
   - `notes-recovery doctor`
3. Only after the demo path works, point the MCP server at one explicit
   `Notes_Forensics_<run_ts>` case root.
4. Keep all reasoning on copied evidence and derived artifacts, not on the live
   Notes store.

## Preferred evidence order

1. Read `review_index.md`.
2. Read the verification preview and pipeline summary.
3. Use `notes-recovery ask-case` for one bounded operator question.
4. Use `notes-recovery case-diff` only when comparing two case roots.
5. Use `notes-recovery public-safe-export` when you need a shareable bundle.

## Bounded MCP entry

```bash
notes-recovery-mcp --case-dir ./output/Notes_Forensics_<run_ts>
```

## Example prompts

- "Review this NoteStore Lab case root and tell me which artifact to inspect first."
- "Wire NoteStore Lab MCP to `./output/Notes_Forensics_2026-04-08_...` and summarize the review-safe surfaces."
- "Compare these two case roots and tell me what changed at the manifest/review layer."
- "Generate a public-safe export plan for this case without exposing raw copied evidence."

## Truth language

- Good: "repo-owned independent skill surface"
- Good: "local copy-first case review skill"
- Forbidden: "officially listed skill" without fresh host-side read-back
- Forbidden: "hosted Notes recovery platform"

## Read next

- `references/README.md`
- `references/INSTALL.md`
- `references/OPENHANDS_MCP_CONFIG.json`
- `references/OPENCLAW_MCP_CONFIG.json`
- `references/CAPABILITIES.md`
- `references/DEMO.md`
- `references/TROUBLESHOOTING.md`
