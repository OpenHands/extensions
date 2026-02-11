# GitHub PR Review

Post focused PR review comments using the GitHub API. Prioritizes important issues over nits.

## Triggers

This skill is activated by the following keywords:

- `/github-pr-review`

## Core Principle

**Less is more.** A review with 2 important comments is better than one with 10 nits. Don't add noise.

## Priority Labels

Only use these three levels. **Skip nits entirely.**

| Label | When to Use |
|-------|-------------|
| 🔴 **Critical** | Must fix: security vulnerabilities, bugs, data loss risks |
| 🟠 **Important** | Should fix: logic errors, missing error handling, breaking changes |
| 🟡 **Suggestion** | Worth considering: significant simplifications, better approaches |

## Key Rules

1. **Filter first**: Only comment on 🔴 Critical and 🟠 Important issues. Skip nits.
2. **One API call**: Bundle all comments into a single review
3. **Approve readily**: If no real issues, just approve
4. **Keep it brief**: Details in inline comments, summary stays short

## What NOT to Comment On

- Style/formatting (leave to linters)
- Minor naming preferences
- "Nice to have" improvements
- Praise for good code (just approve)