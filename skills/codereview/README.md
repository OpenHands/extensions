# Code Review

Focused code review that prioritizes critical issues over style nits. Use when reviewing pull requests or merge requests to identify important issues and provide actionable feedback.

## Triggers

This skill is activated by the following keywords:

- `/codereview`

## Core Principle

**Less is more.** A useful review catches real problems. A noisy review wastes everyone's time and trains authors to ignore feedback. Only comment when it matters.

## Priority Levels

| Priority | When to Use |
|----------|-------------|
| 🔴 **Critical** | Security vulnerabilities, bugs that cause crashes/data loss, breaking API changes |
| 🟠 **Important** | Logic errors, missing error handling, performance issues, missing tests |
| 🟡 **Suggestion** | Significant complexity that could be simplified, better approaches |

## What NOT to Comment On

- Style preferences (leave to linters)
- Minor naming suggestions
- "Nice to have" improvements
- Praise for good code (just approve)
- Suggestions for trivial test additions

**If a PR is good, approve it.** Don't add noise.