---
name: test-improvement-workflow
description: >
  Concise orchestrator for auditing, prioritizing, validating, and implementing
  test-suite improvements using Dave Farley's 8 properties. Use when asked to
  improve test quality, refactor tests, or audit tests and fix them.
triggers:
  - test improvement workflow
  - test-improvement-workflow
  - improve test quality
  - refactor tests
  - audit tests and fix them
version: 1.0.0
metadata:
  openhands:
    requires:
      bins: ["grep", "pytest"]
---

# Test Improvement Workflow

Use this skill as the top-level orchestrator when a user wants an end-to-end test quality improvement pass. It coordinates Paul Hammond's external companion skills plus three smaller reference skills in this repository:

- `test-prioritization-framework`
- `test-validation-checklist`
- `test-improvement-patterns`

## External prerequisites

This workflow depends on four external skills authored by Paul Hammond:

| Skill | Purpose | Source |
|---|---|---|
| `test-design-reviewer` | Audit tests against Dave Farley's 8 properties | `https://github.com/citypaul/.dotfiles/tree/main/claude/.claude/skills/test-design-reviewer` |
| `tdd` | RED -> GREEN -> REFACTOR workflow for new code | `https://github.com/citypaul/.dotfiles/tree/main/claude/.claude/skills/tdd` |
| `refactoring` | Safe behavior-preserving changes | `https://github.com/citypaul/.dotfiles/tree/main/claude/.claude/skills/refactoring` |
| `testing` | Test-writing and edge-case guidance | `https://github.com/citypaul/.dotfiles/tree/main/claude/.claude/skills/testing` |

Install those skills before using this workflow. This repository does not bundle them.

## The 7-step workflow

1. **Audit**
   - Run `test-design-reviewer` across the relevant test files.
   - Capture property scores, the Farley Score, and all raw recommendations.

2. **Consolidate and prioritize**
   - Merge recommendations from every audit section into one deduplicated list.
   - Open `test-prioritization-framework` to classify issues as CRITICAL, HIGH, or MEDIUM.

3. **Present the plan**
   - Always show the prioritized improvements table to the user.
   - Do this even for exemplary suites with high scores.
   - Let the user choose which validated improvements to implement.

4. **Validate each recommendation**
   - Before changing code, open `test-validation-checklist`.
   - Confirm every proposed fix maps to a real issue in the codebase.
   - Remove or narrow any recommendation that is unsupported.

5. **Create the implementation plan**
   - Convert approved improvements into concrete tasks.
   - Assign the right companion skill for each task.

6. **Execute in phases**
   - Open `test-improvement-patterns` for implementation patterns and execution guidance.
   - Commit after each meaningful phase so improvements stay reversible.

7. **Re-audit in a fresh conversation**
   - Run the workflow again in a new conversation for an unbiased reassessment.
   - Do not preload target scores or expected outcomes.

## Skill assignment rules

| Task type | Primary skill |
|---|---|
| Audit current tests | `test-design-reviewer` |
| Add new production or test helper code | `tdd` |
| Restructure existing tests without changing behavior | `refactoring` |
| Add edge-case notes or testing-focused comments | `testing` |
| Validate suspected issues against code | `test-validation-checklist` |
| Rank and present improvements | `test-prioritization-framework` |
| Apply common improvement patterns | `test-improvement-patterns` |

## Operating rules

- Reliability issues come before readability and convenience improvements.
- Always present the prioritized table before implementation.
- Never implement an improvement until it has been validated against the actual code.
- Use TDD for genuinely new behavior and refactoring for behavior-preserving cleanup.
- Recommend a fresh re-audit after implementation.

## Quick start checklist

When invoked, follow this sequence:

1. Audit with `test-design-reviewer`.
2. Consolidate findings into one deduplicated list.
3. Use `test-prioritization-framework` to rank them.
4. Show the prioritized table to the user.
5. Use `test-validation-checklist` to verify each proposed fix.
6. After approval, execute with `tdd`, `refactoring`, `testing`, and `test-improvement-patterns`.
7. Recommend a new-conversation re-audit.
