# Test Improvement Workflow

Systematic workflow for improving test suite quality using Dave Farley's 8 properties. It orchestrates companion skills into a complete audit-prioritize-validate-implement cycle.

## What it does

This skill guides an agent through a 7-step process:

1. Audit the existing tests
2. Prioritize issues by reliability and impact
3. Present a consolidated improvement plan
4. Validate that each proposed fix matches a real code issue
5. Assign the right companion skill to each task
6. Execute improvements in phases
7. Re-audit in a new conversation

## Companion skills

This workflow expects these skills to be available:

- `test-design-reviewer`
- `tdd`
- `refactoring`
- `testing`

## Triggers

This skill is activated by keywords such as:

- `test improvement workflow`
- `improve test quality`
- `refactor tests`
- `audit tests and fix them`

## Details

See [SKILL.md](./SKILL.md) for the full workflow, prioritization framework, validation rules, and execution guidance.
