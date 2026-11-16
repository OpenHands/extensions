# Ponder

Multi-pass, coverage-gated deliberation loop and code review CLI for AI coding agents. Enforces an on-disk coverage gate where 100% of enumerated units must be explicitly graded across lens dimensions, four structured perspectives (skeptic, builder, dreamer, empath) deliberate across passes, and the review halts only when two consecutive passes produce zero ledger deltas.

## Triggers

This skill is activated by the following keyword:

- `/ponder`

## Details

See [SKILL.md](./SKILL.md) for the full skill content including review workflow, session state machine, and ledger reconciliation commands.
