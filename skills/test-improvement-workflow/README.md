# Test Improvement Workflow

Concise orchestrator for improving test suites end to end. It coordinates an audit, reliability-first prioritization, validation against real code, implementation planning, and a fresh re-audit.

## What it does

This skill guides an agent through a 7-step process:

1. Audit the existing tests
2. Consolidate and prioritize findings
3. Present a user-facing improvement table
4. Validate that each suggestion matches a real code issue
5. Plan implementation tasks
6. Execute improvements in phases
7. Re-audit in a new conversation

## Related skills

This orchestrator points to three local reference skills:

- `test-prioritization-framework`
- `test-validation-checklist`
- `test-improvement-patterns`

It also expects Paul Hammond's external companion skills:

- `test-design-reviewer`
- `tdd`
- `refactoring`
- `testing`

See [SKILL.md](./SKILL.md) for the workflow and dependency details.
