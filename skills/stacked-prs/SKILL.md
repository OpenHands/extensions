---
name: stacked-prs
description: Guide for breaking large pull requests into stacked, dependent PRs that are easier to review. Use when (1) a PR is too large (>400 lines), (2) splitting an existing big PR into smaller pieces, (3) planning a multi-part feature implementation, (4) setting up a stacked PR workflow, or (5) managing dependent branches and rebasing cascades.
---

# Stacked PRs Workflow

Stacked PRs (or "stacked diffs") break large changes into a series of small, dependent PRs where each branch builds on the previous one. This creates a narrative that walks reviewers through changes logically.

## Why Stack PRs

- **200-line PRs get reviewed in minutes; 2000-line PRs sit for days**
- Smaller changes are easier to understand and review thoroughly
- Developers stay productive while waiting for reviews
- Reduces bug risk through better review quality
- Creates a story that guides reviewers through the change

## Quick Reference

### Creating a Stack (Manual Git)

```bash
# Start from main
git checkout main && git pull

# Create first branch
git checkout -b feature/auth-01-models
# ... make changes, commit ...
git push -u origin feature/auth-01-models

# Create second branch FROM first
git checkout -b feature/auth-02-api
# ... make changes, commit ...
git push -u origin feature/auth-02-api

# Create third branch FROM second
git checkout -b feature/auth-03-ui
# ... make changes, commit ...
git push -u origin feature/auth-03-ui
```

### Creating PRs for the Stack

Open PRs with the correct base branches:
- PR #1: `feature/auth-01-models` → `main`
- PR #2: `feature/auth-02-api` → `feature/auth-01-models`
- PR #3: `feature/auth-03-ui` → `feature/auth-02-api`

### Updating After Review Feedback (Manual Rebase)

When PR #1 changes, update downstream PRs:

```bash
# Update PR #1
git checkout feature/auth-01-models
# ... make changes, commit, push ...

# Rebase PR #2 onto updated PR #1
git checkout feature/auth-02-api
git rebase feature/auth-01-models
git push --force-with-lease

# Rebase PR #3 onto updated PR #2
git checkout feature/auth-03-ui
git rebase feature/auth-02-api
git push --force-with-lease
```

### After PR #1 Merges

Rebase remaining PRs onto main and update PR base branches:

```bash
git checkout main && git pull

# Rebase PR #2 onto main
git checkout feature/auth-02-api
git rebase main
git push --force-with-lease
# Update PR #2's base branch to main (via GitHub UI or CLI)

# Rebase PR #3 onto updated PR #2
git checkout feature/auth-03-ui
git rebase feature/auth-02-api
git push --force-with-lease
```

## Breaking Down a Large PR

When splitting an existing large PR, analyze by logical layers:

### Decomposition Strategies

1. **By Layer** (most common)
   - Data models / schemas
   - Business logic / services
   - API endpoints / controllers
   - UI components
   - Tests

2. **By Feature Slice**
   - Core functionality first
   - Edge cases and error handling
   - Optimizations and polish

3. **By Dependency Order**
   - What can exist independently?
   - What requires something else to be merged first?

### Decision Framework

For each logical chunk, ask:
- Can this be reviewed independently?
- Does it pass tests on its own?
- Is it <400 lines of meaningful change?
- Does it tell a coherent story?

## PR Description Template

For stacked PRs, always include stack context in descriptions. See `references/pr-template.md` for a copy-paste template.

Key elements:
- Stack overview with links to all PRs
- Position indicator (e.g., "Part 2 of 4")
- What THIS PR specifically accomplishes
- Any special review considerations

## Tooling Options

### Graphite CLI (Recommended for Teams)

Automates rebasing, PR creation, and merge orchestration:

```bash
# Install
npm install -g @withgraphite/graphite-cli

# Create stacked branches
gt branch create feature/models
gt branch create feature/api      # automatically stacks on feature/models
gt branch create feature/ui       # automatically stacks on feature/api

# Submit stack as PRs
gt stack submit

# Sync after changes (automatic rebase cascade)
gt stack sync
```

### Manual Git (No Dependencies)

Use the commands in Quick Reference above. More effort but works everywhere.

### GitHub CLI Helpers

```bash
# Create PR with specific base
gh pr create --base feature/auth-01-models --title "Part 2: Auth API"

# Update PR base branch after merge
gh pr edit 123 --base main
```

## Common Pitfalls

1. **Circular dependencies** - Each PR must be mergeable without later PRs
2. **Breaking tests** - Each PR in stack should pass CI independently
3. **Force-push without --force-with-lease** - Can lose collaborator changes
4. **Forgetting to update base branches** - After merge, update remaining PRs' base
5. **Stack too deep** - Keep stacks to 3-5 PRs; beyond that, complexity increases

## Maintaining Stack Coherence

The hardest part of stacked PRs is maintaining coherence when changes cascade:

1. **Rebase early and often** - Don't let branches diverge too far
2. **Small, focused commits** - Easier to resolve conflicts
3. **Clear commit boundaries** - Each commit should be atomic
4. **Communicate with reviewers** - Let them know when you've rebased

## Further Reading

See `references/pr-template.md` for PR description template.
See `references/advanced-workflows.md` for complex scenarios like mid-stack changes and handling merge conflicts.
