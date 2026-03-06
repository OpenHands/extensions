---
name: release-notes
description: Generate consistent, well-structured release notes from git history. Triggered on release tags following semver patterns (v*.*.*) to produce categorized changelog with breaking changes, features, fixes, and contributor attribution.
triggers:
- /release-notes
- /releasenotes
---

# Release Notes Generator Plugin

Automates the generation of standardized release notes for OpenHands repositories. This plugin can be triggered via GitHub Actions on release tags matching semver patterns (e.g., `v*.*.*`) or manually invoked.

## Features

- **Automatic tag detection**: Finds the previous release tag to determine the commit range
- **Categorized changes**: Groups commits into Breaking Changes, Features, Bug Fixes, Documentation, and Internal sections
- **Contributor attribution**: Includes PR numbers and author usernames for each change
- **New contributor highlighting**: Identifies and celebrates first-time contributors
- **Flexible output**: Can update GitHub release notes or generate CHANGELOG.md entries

## Quick Start

### As a GitHub Action

Copy the workflow file to your repository:

```bash
mkdir -p .github/workflows
curl -o .github/workflows/release-notes.yml \
  https://raw.githubusercontent.com/OpenHands/extensions/main/plugins/release-notes/workflows/release-notes.yml
```

Configure required secrets (see the README for details).

### Manual Invocation

Use the `/release-notes` trigger in an OpenHands conversation to generate release notes for the current repository.

## Release Notes Format

Generated release notes follow this structure:

```markdown
## [v1.2.0] - 2026-03-06

### ⚠️ Breaking Changes
- Remove deprecated `--legacy` CLI flag (#456) @maintainer

### ✨ New Features
- Add support for Claude Sonnet 4.6 model (#445) @contributor1

### 🐛 Bug Fixes
- Fix WebSocket reconnection on network interruption (#451) @contributor3

### 📚 Documentation
- Update installation guide (#442) @contributor2

### 👥 New Contributors
- @contributor3 made their first contribution in #451

**Full Changelog**: https://github.com/org/repo/compare/v1.1.0...v1.2.0
```

## Change Categorization

Changes are categorized based on:

1. **Conventional commit prefixes**: `feat:`, `fix:`, `docs:`, `chore:`, `BREAKING:`
2. **PR labels**: `breaking-change`, `bug`, `enhancement`, `documentation`

| Category | Commit Prefixes | PR Labels |
|----------|-----------------|-----------|
| Breaking Changes | `BREAKING:`, `!:` suffix | `breaking-change`, `breaking` |
| Features | `feat:`, `feature:` | `enhancement`, `feature` |
| Bug Fixes | `fix:`, `bugfix:` | `bug`, `bugfix` |
| Documentation | `docs:` | `documentation`, `docs` |
| Internal | `chore:`, `ci:`, `refactor:`, `test:` | `internal`, `chore`, `ci` |

## Configuration

See the [README](./README.md) for full configuration options and workflow setup instructions.
