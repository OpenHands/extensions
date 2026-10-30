---
name: fix-merge-conflicts
description: Resolve git merge conflicts intelligently by understanding the intent of both changes. Handles code conflicts, configuration file merges, and lock file reconciliation.
triggers:
- /fix-conflicts
- /resolve-conflicts
---

# Fix Merge Conflicts

Intelligently resolve git merge conflicts while preserving the intent of both changes.

## Process

1. **Understand the conflict**: Analyze both sides of each conflict
2. **Determine intent**: Understand what each change was trying to accomplish
3. **Resolve intelligently**: Merge changes in a way that preserves both intents
4. **Verify correctness**: Ensure the resolution doesn't break functionality

## Conflict Types

### Code Conflicts
- Parallel changes to the same function
- Competing refactors
- Feature additions that overlap

### Configuration Conflicts
- Package.json, Cargo.toml, pyproject.toml changes
- Environment configuration files
- Build configuration

### Lock File Conflicts
- package-lock.json
- yarn.lock, pnpm-lock.yaml
- Cargo.lock, poetry.lock

### Documentation Conflicts
- README updates
- Changelog entries
- Comment modifications

## Resolution Strategies

- **Both valid**: Combine both changes when they don't conflict semantically
- **One supersedes**: Choose the more complete or correct change
- **Requires redesign**: When changes are fundamentally incompatible, suggest a new approach
- **Lock files**: Regenerate rather than manually merge
