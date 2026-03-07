# Release Notes Generator Plugin

Automated release notes generation using OpenHands agents. This plugin provides GitHub workflows that generate consistent, well-structured release notes when release tags are pushed.

## Quick Start

Copy the workflow file to your repository:

```bash
mkdir -p .github/workflows
curl -o .github/workflows/release-notes.yml \
  https://raw.githubusercontent.com/OpenHands/extensions/main/plugins/release-notes/workflows/release-notes.yml
```

Then configure the required secrets (see [Installation](#installation) below).

## Features

- **Automatic Tag Detection**: Automatically finds the previous release tag to determine the commit range
- **Categorized Changes**: Groups user-facing updates into Breaking Changes, Features, Bug Fixes, Documentation, and Internal sections
- **PR-Level Summaries**: Uses merged PR titles when available and collapses multiple commits from the same PR into one entry
- **Conventional Commits Support**: Categorizes based on commit prefixes (`feat:`, `fix:`, `docs:`, etc.)
- **PR Label Support**: Also categorizes based on GitHub PR labels
- **Contributor Attribution**: Includes PR numbers and author usernames for each change
- **New Contributor Highlighting**: Identifies and celebrates first-time contributors
- **Flexible Output**: Updates GitHub release notes directly or outputs for CHANGELOG.md

## Plugin Contents

```
plugins/release-notes/
├── README.md              # This file
├── SKILL.md               # Plugin definition
├── action.yml             # Composite GitHub Action
├── scripts/               # Python scripts
│   └── generate_release_notes.py
└── workflows/             # Example GitHub workflow files
    └── release-notes.yml
```

## Installation

### 1. Copy the Workflow File

Copy the workflow file to your repository's `.github/workflows/` directory:

```bash
mkdir -p .github/workflows
curl -o .github/workflows/release-notes.yml \
  https://raw.githubusercontent.com/OpenHands/extensions/main/plugins/release-notes/workflows/release-notes.yml
```

### 2. Configure Secrets

Add the following secrets in your repository settings (**Settings → Secrets and variables → Actions**):

| Secret | Required | Description |
|--------|----------|-------------|
| `GITHUB_TOKEN` | Auto | Provided automatically by GitHub Actions |

**Note**: The default `GITHUB_TOKEN` is sufficient for most use cases. For repositories that need elevated permissions, use a personal access token.

### 3. Customize the Workflow (Optional)

Edit the workflow file to customize:

```yaml
- name: Generate Release Notes
  uses: OpenHands/extensions/plugins/release-notes@main
  with:
    # The release tag to generate notes for
    tag: ${{ github.ref_name }}
    
    # Optional: Override previous tag detection
    # previous-tag: v1.0.0
    
    # Include internal/infrastructure changes (default: false)
    include-internal: false
    
    # Output format: 'release' (GitHub release) or 'changelog' (CHANGELOG.md)
    output-format: release
    
    # Secrets
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Usage

### Automatic Triggers

Release notes are automatically generated when:

1. A tag matching `v[0-9]+.[0-9]+.[0-9]+*` is pushed (e.g., `v1.2.0`, `v2.0.0-beta.1`)

### Manual Triggering

You can also manually trigger release notes generation:

1. Go to **Actions** in your repository
2. Select the "Generate Release Notes" workflow
3. Click **Run workflow**
4. Enter the tag to generate notes for

## Action Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `tag` | Yes | - | The release tag to generate notes for |
| `previous-tag` | No | Auto-detect | Override automatic detection of previous release |
| `include-internal` | No | `false` | Include internal/infrastructure changes |
| `output-format` | No | `release` | Output format: `release` or `changelog` |
| `github-token` | Yes | - | GitHub token for API access |

## Action Outputs

| Output | Description |
|--------|-------------|
| `release-notes` | The generated release notes in markdown format |
| `previous-tag` | The detected or provided previous release tag |
| `commit-count` | Number of commits included in the release |
| `contributor-count` | Number of unique contributors |
| `new-contributor-count` | Number of first-time contributors |

## Release Notes Structure

Generated release notes follow this format:

```markdown
## [v1.2.0] - 2026-03-06

### ⚠️ Breaking Changes
- Remove deprecated `--legacy` CLI flag (#456) @maintainer

### ✨ New Features
- Add support for Claude Sonnet 4.6 model (#445) @contributor1
- Implement parallel tool execution (#438) @contributor2

### 🐛 Bug Fixes
- Fix WebSocket reconnection on network interruption (#451) @contributor3
- Resolve memory leak in long-running sessions (#447) @maintainer

### 📚 Documentation
- Update installation guide for v1.2 (#442) @contributor2

### 🏗️ Internal/Infrastructure
- Upgrade CI to use Node 20 (#440) @maintainer

### 👥 New Contributors
- @contributor3 made their first contribution in #451

**Full Changelog**: https://github.com/org/repo/compare/v1.1.0...v1.2.0
```

## Change Categorization

Changes are categorized using two methods:

### 1. Conventional Commit Prefixes

| Prefix | Category |
|--------|----------|
| `BREAKING:` or `!:` suffix | ⚠️ Breaking Changes |
| `feat:`, `feature:` | ✨ New Features |
| `fix:`, `bugfix:` | 🐛 Bug Fixes |
| `docs:` | 📚 Documentation |
| `chore:`, `ci:`, `refactor:`, `test:`, `build:` | 🏗️ Internal/Infrastructure |

### 2. PR Labels

| Labels | Category |
|--------|----------|
| `breaking-change`, `breaking` | ⚠️ Breaking Changes |
| `enhancement`, `feature` | ✨ New Features |
| `bug`, `bugfix` | 🐛 Bug Fixes |
| `documentation`, `docs` | 📚 Documentation |
| `internal`, `chore`, `ci`, `dependencies` | 🏗️ Internal/Infrastructure |

## Content Guidelines

The generator follows these principles:

- **Concise but informative**: Uses one line per merged PR where possible instead of listing every commit
- **User-focused**: Prioritizes categorized, user-facing changes and omits uncategorized noise from the default output
- **Scannable**: Easy to quickly find relevant changes
- **Imperative mood**: Uses "Add feature" not "Added feature"
- **Attribution**: Includes PR number and author for traceability

## Customizing Output

### Excluding Internal Changes

By default, internal/infrastructure changes are excluded. To include them:

```yaml
- uses: OpenHands/extensions/plugins/release-notes@main
  with:
    include-internal: true
```

### Generating CHANGELOG.md Entries

To generate output suitable for a CHANGELOG.md file:

```yaml
- uses: OpenHands/extensions/plugins/release-notes@main
  with:
    output-format: changelog
```

Then use the output in a subsequent step:

```yaml
- name: Update CHANGELOG
  run: |
    echo "${{ steps.release-notes.outputs.release-notes }}" >> CHANGELOG.md
```

## Troubleshooting

### Release Notes Not Generated

1. Check that the tag matches the semver pattern: `v[0-9]+.[0-9]+.[0-9]+*`
2. Verify the workflow file is in `.github/workflows/`
3. Check the Actions tab for error messages

### Wrong Previous Tag Detected

Use the `previous-tag` input to override automatic detection:

```yaml
previous-tag: v1.0.0
```

### Missing Contributors

The generator uses the GitHub API to fetch PR authors. Ensure:
1. Commits are associated with merged PRs
2. The `GITHUB_TOKEN` has read access to pull requests

## Security

- Uses the default `GITHUB_TOKEN` for API access
- No secrets are persisted or logged
- Read-only access to repository history and PRs

## Contributing

See the main [extensions repository](https://github.com/OpenHands/extensions) for contribution guidelines.

## License

This plugin is part of the OpenHands extensions repository. See [LICENSE](../../LICENSE) for details.
