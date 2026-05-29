# Evidence-Based Citations

Back factual claims and field values with official, verifiable sources. Use when the user asks to fill fields, answer questions, or make claims that must be supported by an exact quote and an official link.

## Triggers

This skill is activated by the following keywords:

- `evidence-based`
- `cite source` / `cite sources`
- `official source` / `official link` / `official documentation`
- `verifiable source`
- `with evidence` / `back with evidence`

## What it does

When activated, the agent reports every field value or factual claim using four labeled lines:

- **Field** - the field name or short claim description
- **Value** - the value being assigned
- **Quote** - the verbatim text from the source supporting the value
- **Source** - the official URL where the quote can be found

## Source rules

- Prefer primary sources (official docs, RFCs, API references, source code).
- Fall back to secondary sources (blogs, forums) only when necessary, and label them.
- The quote must appear verbatim at the source URL.
- If no official source can be found, say `Source: No official source found.` rather than fabricating a reference.

See [`SKILL.md`](./SKILL.md) for the full prompt the agent loads when this skill is triggered.
