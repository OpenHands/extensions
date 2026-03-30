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
- **Agent-Based Summaries**: Uses an OpenHands agent to judge significance, merge related PRs, and decide what is worth mentioning
- **Structured GitHub Context**: Feeds the agent merged PR titles, labels, bodies, authors, and contributor information for the release range
- **Conventional Commits Support**: Uses commit prefixes (`feat:`, `fix:`, `docs:`, etc.) as categorization hints for the agent
- **PR Label Support**: Uses GitHub PR labels as additional hints for the agent
- **Contributor Attribution**: Includes PR numbers and author usernames for each change the agent keeps
- **Attribution Validation**: Fails the workflow if any release-range PR/commit or corresponding author is omitted from the final notes
- **Deterministic Coverage Appendix**: When the agent omits lower-signal PRs, the action appends a compact `### 🔎 Small Fixes/Internal Changes` appendix grouped by author so every PR and author in the release range is still listed somewhere in the output
- **New Contributor Highlighting**: Identifies first-time human contributors from merged PR history and excludes bot accounts
- **Flexible Output**: Updates GitHub release notes directly or outputs for CHANGELOG.md

## Plugin Contents

```
plugins/release-notes/
├── README.md              # This file
├── SKILL.md               # Plugin definition
├── action.yml             # Composite GitHub Action
├── scripts/               # Python scripts
│   ├── agent_script.py    # OpenHands agent orchestration
│   ├── generate_release_notes.py
│   ├── prompt.py
│   └── validate_release_notes.py
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
| `LLM_API_KEY` | Yes | API key for the LLM used by the OpenHands agent |
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

    # Optional model override
    # llm-model: anthropic/claude-sonnet-4-5-20250929

    # Secrets
    llm-api-key: ${{ secrets.LLM_API_KEY }}
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
| `llm-model` | No | `anthropic/claude-sonnet-4-5-20250929` | LLM used by the OpenHands agent |
| `llm-base-url` | No | - | Optional custom LLM endpoint |
| `llm-api-key` | Yes | - | API key for the OpenHands agent's LLM |
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

The agent receives deterministic categorization hints, but it makes the final decision about significance, grouping, and which entries to keep.

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

- **Conversational overview**: Starts with a short plain-language summary of the release before the detailed sections
- **Concise but informative**: The agent decides which changes matter and can merge related PRs into a single higher-signal bullet
- **User-focused**: The agent prioritizes end-user and client-developer impact over low-level implementation detail
- **Internal changes stay secondary**: CI churn, prompt tweaks, workflow plumbing, contributor ergonomics, and similar toolkit-maintainer details belong in `### 🔎 Small Fixes/Internal Changes` unless they are unusually significant
- **Scannable**: Easy to quickly find relevant changes
- **Imperative mood**: Uses "Add feature" not "Added feature"
- **Attribution**: Includes PR number and author for traceability

## Validation Guardrail

After the agent writes `release_notes.md`, the action runs `scripts/validate_release_notes.py`.
That validator rebuilds the deterministic PR/author context for the same tag range and checks that the final notes:

- include at least one explicit PR or commit reference in every user-facing change bullet
- include the author handle for every referenced PR or commit
- do not reference unknown PRs or commits
- cover every PR/commit in the release range somewhere in the markdown

If the agent keeps the main sections concise and omits lower-signal PRs, `agent_script.py` inserts a compact `### 🔎 Small Fixes/Internal Changes` appendix before the full changelog link. That appendix is grouped by author so the output remains readable while still being exhaustive.

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

### Missing LLM Credentials

Make sure `LLM_API_KEY` is configured in repository secrets and passed to the action.

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
