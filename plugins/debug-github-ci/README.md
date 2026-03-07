# Debug GitHub CI

Automated debugging of GitHub Actions CI failures using OpenHands agents.

## Overview

This extension provides **dual-mode functionality**:

1. **Skill Mode**: A knowledge skill (`SKILL.md`) that provides guidance and context for debugging CI failures interactively via OpenHands conversations.

2. **Plugin Mode**: An executable GitHub Action (`action.yml`) that can be triggered automatically when CI fails, running an autonomous debug agent.

Use **skill mode** when working interactively with OpenHands to debug CI issues. Use **plugin mode** to automate CI failure analysis in your GitHub workflows.

## Quick Start

Copy the workflow file to your repository:

```bash
mkdir -p .github/workflows
curl -o .github/workflows/debug-ci-failure.yml \
  https://raw.githubusercontent.com/OpenHands/extensions/main/plugins/debug-github-ci/workflows/debug-ci-failure.yml
```

Then configure the required secrets (see [Installation](#installation) below).

## Features

- **Automatic CI Failure Analysis**: Triggered when workflow runs fail
- **Log Analysis**: Fetches and analyzes failed job logs to identify root causes
- **Actionable Suggestions**: Posts comments with specific fixes and commands
- **Error Pattern Recognition**: Identifies common CI failure patterns
- **Context-Aware**: Considers recent commits and PR changes

## Plugin Contents

```
plugins/debug-github-ci/
├── README.md              # This file
├── action.yml             # Composite GitHub Action
├── skills/                # Symbolic links to debug skills
│   └── debug-github-ci -> ../../../skills/debug-github-ci
├── workflows/             # Example GitHub workflow files
│   └── debug-ci-failure.yml
└── scripts/               # Python scripts for debug execution
    ├── agent_script.py    # Main CI debug agent script
    └── prompt.py          # Prompt template for debugging
```

Notes:
- The marketplace manifest uses the repo-wide `pluginRoot: "./skills"`, so `source: "./debug-github-ci"` resolves to `skills/debug-github-ci`.
- The `plugins/debug-github-ci/skills/debug-github-ci` symlink mirrors the `pr-review` plugin pattern so the plugin bundle can reference the matching skill content without duplicating `SKILL.md`.

## Installation

### 1. Copy the Workflow File

Copy the workflow file to your repository's `.github/workflows/` directory:

```bash
mkdir -p .github/workflows
curl -o .github/workflows/debug-ci-failure.yml \
  https://raw.githubusercontent.com/OpenHands/extensions/main/plugins/debug-github-ci/workflows/debug-ci-failure.yml
```

### 2. Configure Secrets

Add the following secrets in your repository settings (**Settings → Secrets and variables → Actions**):

| Secret | Required | Description |
|--------|----------|-------------|
| `LLM_API_KEY` | Yes | API key for your LLM provider |
| `GITHUB_TOKEN` | Auto | Provided automatically by GitHub Actions |

### 3. Customize the Workflow (Optional)

Edit the workflow file to customize:

```yaml
- name: Debug CI Failure
  uses: OpenHands/extensions/plugins/debug-github-ci@main
  with:
    # LLM model to use
    llm-model: anthropic/claude-sonnet-4-5-20250929
    
    # Secrets
    llm-api-key: ${{ secrets.LLM_API_KEY }}
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Usage

### Automatic Triggers

CI debugging is automatically triggered when:

1. A workflow run fails on the repository
2. The `debug-ci` label is added to a PR with failed checks

### Manual Trigger

You can manually trigger debugging:

1. Go to **Actions** tab
2. Select **Debug CI Failure** workflow
3. Click **Run workflow**
4. Enter the failed run ID

## Action Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `llm-model` | No | `anthropic/claude-sonnet-4-5-20250929` | LLM model to use |
| `llm-base-url` | No | `''` | Custom LLM endpoint URL |
| `run-id` | No | Auto | Specific workflow run ID to debug |
| `extensions-repo` | No | `OpenHands/extensions` | Extensions repository |
| `extensions-version` | No | `main` | Git ref (tag, branch, or SHA) |
| `llm-api-key` | Yes | - | LLM API key |
| `github-token` | Yes | - | GitHub token for API access |

## What Gets Analyzed

The agent analyzes:

1. **Failed job logs**: Console output from failed steps
2. **Error messages**: Specific error patterns and stack traces
3. **Recent commits**: Changes that may have caused the failure
4. **Workflow configuration**: Issues in the workflow YAML
5. **Dependencies**: Version conflicts or missing packages

## Output

The agent posts a comment with:

- **Root Cause Analysis**: What caused the failure
- **Suggested Fixes**: Specific commands or code changes
- **Prevention Tips**: How to avoid similar failures

## Troubleshooting

### Debug Not Triggered

1. Ensure the workflow file is in `.github/workflows/`
2. Verify secrets are configured correctly
3. Check that the workflow has `workflow_run` trigger permissions

### Analysis Incomplete

1. Check if logs are available (some expire after 90 days)
2. Verify the `GITHUB_TOKEN` has read access to workflow logs
3. Increase timeout if analysis takes too long

## Security

- Uses `workflow_run` event for secure access to secrets
- Only analyzes public workflow logs
- Does not execute any code from the failed run

## Contributing

See the main [extensions repository](https://github.com/OpenHands/extensions) for contribution guidelines.

## License

This plugin is part of the OpenHands extensions repository. See [LICENSE](../../LICENSE) for details.
