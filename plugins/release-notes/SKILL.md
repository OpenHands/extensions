---
name: release-notes
description: Generate consistent, well-structured release notes from git history. Triggered on release tags following semver patterns (v*.*.*) to produce categorized changelog with breaking changes, features, fixes, and contributor attribution.
triggers:
- /release-notes
---

# Release Notes Generator Plugin

Automates the generation of standardized release notes for OpenHands repositories using an OpenHands agent. The agent reviews the release range, judges significance, groups related PRs, and produces concise markdown for GitHub releases or changelogs.

## Features

- **Automatic tag detection**: Finds the previous release tag to determine the commit range
- **Agent-based editing**: Lets the agent decide which changes matter, open with a short conversational summary, and group related PRs into higher-signal summaries while keeping toolkit-maintainer-only details out of the main sections unless they are unusually significant
- **Structured GitHub context**: Supplies PR titles, labels, descriptions, and contributor metadata to guide the agent
- **Contributor attribution**: Includes PR numbers and author usernames for each change
- **Attribution validation**: Verifies every change bullet contains explicit PR/commit references and the matching author handles
- **Full coverage appendix**: Appends a compact `### 🔎 Small Fixes/Internal Changes` section grouped by author when needed so every PR and author in the release range is still listed somewhere in the final markdown
- **New contributor highlighting**: Identifies first-time human contributors from merged PR history and excludes bot accounts
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
