# Code Review

Rigorous code review focusing on data structures, simplicity, security, pragmatism, and risk/safety evaluation. Provides brutally honest, actionable feedback on pull requests or merge requests, including a risk assessment (🟢 Low / 🟡 Medium / 🔴 High) for every review.

This skill combines the previous `code-review` (standard) and `codereview-roasted` skills into a single unified review skill.

## Triggers

This skill is activated by the following keywords:

- `/codereview`
- `/codereview-roasted` (backward-compatible alias)

## Details

See [SKILL.md](./SKILL.md) for the full skill content including review scenarios, output format, and communication style guidelines.

The risk evaluation framework is defined in [`references/risk-evaluation.md`](references/risk-evaluation.md) and classifies PR risk based on pattern conformance, security sensitivity, infrastructure dependencies, blast radius, and core system impact.
