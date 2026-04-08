---
name: notestorelab-case-review
description: Guide one bounded NoteStore Lab case review without turning the repo into a hosted platform.
---

# NoteStore Lab Case Review

Use this skill when an agent is reviewing one NoteStore Lab case root or the
public-safe demo surface.

## Product truth

- Recovery is the main product.
- AI and MCP are review layers, not the recovery engine.
- Stay local, copy-first, and case-root-driven.
- Prefer derived artifacts before raw copied evidence.
- Do not treat the live Notes store as a target.
- Do not describe this repo as a hosted or multi-tenant platform.

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

## Proof path

1. `notes-recovery demo`
2. `notes-recovery ai-review --demo`
3. `notes-recovery ask-case --demo --question "What should I inspect first?"`
4. `notes-recovery doctor`

## Truth language

- Good: "repo-owned independent skill surface"
- Good: "local copy-first case review skill"
- Forbidden: "officially listed skill" without fresh host-side read-back
- Forbidden: "hosted Notes recovery platform"
