# Test Improvement Plugin

Bundle the full test-improvement workflow into one installable plugin.

## Included skills

| Skill | Role |
|---|---|
| `test-improvement-workflow` | Top-level orchestrator for audit, prioritization, validation, execution, and re-audit |
| `test-prioritization-framework` | Reliability-first ranking of audit findings |
| `test-validation-checklist` | Checklist for proving each recommendation matches a real code issue |
| `test-improvement-patterns` | Safe execution loops and recurring test-cleanup patterns |

## Quick start

Use `test-improvement-workflow` as the entry point. It walks through the full seven-step process and points to the bundled companion skills when needed.

## Notes

- This plugin packages the repo-local test-improvement skills together for easier installation.
- The workflow still references external companion skills (`test-design-reviewer`, `tdd`, `refactoring`, `testing`) for audit and implementation work that is not defined in this repository.
