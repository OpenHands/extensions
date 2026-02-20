# PR Review Plugin

Automated pull request review using OpenHands agents. This plugin provides GitHub workflows that automatically review PRs with detailed, inline code review comments.

## Quick Start

Copy both workflow files to your repository:

```bash
mkdir -p .github/workflows
curl -o .github/workflows/pr-review-by-openhands.yml \
  https://raw.githubusercontent.com/OpenHands/extensions/main/.github/workflows/pr-review-by-openhands.yml
curl -o .github/workflows/pr-review-evaluation.yml \
  https://raw.githubusercontent.com/OpenHands/extensions/main/.github/workflows/pr-review-evaluation.yml
```

Then configure the required secrets (see [Installation](#installation) below).

## Features

- **Automated PR Reviews**: Triggered when PRs are opened, marked ready, or when a reviewer is requested
- **Inline Code Comments**: Posts review comments directly on specific lines of code
- **Two Review Styles**:
  - `standard` - Balanced code review covering style, readability, and security
  - `roasted` - Linus Torvalds-style brutally honest feedback focusing on data structures, simplicity, and pragmatism
- **A/B Testing**: Support for testing multiple LLM models
- **Review Context Awareness**: Considers previous reviews and unresolved threads
- **Observability**: Optional Laminar integration for tracing and evaluation

## Plugin Contents

```
plugins/pr-review/
├── README.md              # This file
├── action.yml             # Composite GitHub Action
├── skills/                # Symbolic links to review skills
│   ├── codereview-roasted -> ../../../skills/codereview-roasted
│   └── github-pr-review -> ../../../skills/github-pr-review
├── workflows/             # Example GitHub workflow files
│   ├── pr-review-by-openhands.yml
│   └── pr-review-evaluation.yml
└── scripts/               # Python scripts for review execution
    ├── agent_script.py    # Main PR review agent script
    ├── prompt.py          # Prompt template for reviews
    └── evaluate_review.py # Evaluation script for merged/closed PRs
```

## Installation

### 1. Copy the Workflow Files

Copy the workflow files to your repository's `.github/workflows/` directory:

```bash
mkdir -p .github/workflows
curl -o .github/workflows/pr-review-by-openhands.yml \
  https://raw.githubusercontent.com/OpenHands/extensions/main/.github/workflows/pr-review-by-openhands.yml
curl -o .github/workflows/pr-review-evaluation.yml \
  https://raw.githubusercontent.com/OpenHands/extensions/main/.github/workflows/pr-review-evaluation.yml
```

### 2. Configure Secrets

Add the following secrets in your repository settings (**Settings → Secrets and variables → Actions**):

| Secret | Required | Description |
|--------|----------|-------------|
| `LLM_API_KEY` | Yes | API key for your LLM provider |
| `GITHUB_TOKEN` | Auto | Provided automatically by GitHub Actions |
| `LMNR_SKILLS_API_KEY` | No | Laminar API key (org-level secret; mapped to `LMNR_PROJECT_API_KEY` env var in workflows) |

**Note**: For repositories that need to post review comments from a bot account, use `ALLHANDS_BOT_GITHUB_PAT` instead of `GITHUB_TOKEN`.

### 3. Customize the Workflow (Optional)

Edit the workflow file to customize:

```yaml
- name: Run PR Review
  uses: OpenHands/extensions/plugins/pr-review@main
  with:
    # LLM model(s) - comma-separated for A/B testing
    llm-model: anthropic/claude-sonnet-4-5-20250929
    
    # Optional: Custom LLM endpoint
    # llm-base-url: https://your-llm-proxy.example.com
    
    # Review style: 'standard' or 'roasted'
    review-style: roasted
    
    # Pin to a specific version (tag, branch, or commit SHA)
    extensions-version: main
    
    # Secrets
    llm-api-key: ${{ secrets.LLM_API_KEY }}
    github-token: ${{ secrets.GITHUB_TOKEN }}
    
    # Optional: Enable Laminar observability
    # lmnr-api-key: ${{ secrets.LMNR_PROJECT_API_KEY }}
```

### 4. Create the Review Label (Optional)

Create a `review-this` label for manual review triggers:

1. Go to **Issues → Labels** in your repository
2. Click **New label**
3. Name: `review-this`
4. Description: `Trigger OpenHands PR review`
5. Click **Create label**

## Usage

### Automatic Triggers

PR reviews are automatically triggered when:

1. A new non-draft PR is opened by a collaborator (author association: `COLLABORATOR`, `MEMBER`, or `OWNER`)
2. A draft PR is marked as ready for review by a collaborator
3. The `review-this` label is added by a user with **write (or higher)** permission
4. `openhands-agent` or `all-hands-bot` is requested as a reviewer by a user with **write (or higher)** permission

### Requesting a Review

Only users with **write (or higher)** permission can trigger a review.

In this workflow, the **triggering user** is `github.actor`: the account that performed the action that started the run (e.g. the person who added the `review-this` label or requested the reviewer) — not necessarily the PR author.

**Option 1: Request as Reviewer**
1. Open the PR
2. Click **Reviewers** in the sidebar
3. Select `openhands-agent` (or `all-hands-bot`) as a reviewer

**Option 2: Add Label**
1. Open the PR
2. Add the `review-this` label

## Action Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `llm-model` | No | `anthropic/claude-sonnet-4-5-20250929` | LLM model(s), comma-separated for A/B testing |
| `llm-base-url` | No | `''` | Custom LLM endpoint URL |
| `review-style` | No | `roasted` | Review style: `standard` or `roasted` |
| `extensions-repo` | No | `OpenHands/extensions` | Extensions repository |
| `extensions-version` | No | `main` | Git ref (tag, branch, or SHA) |
| `llm-api-key` | Yes | - | LLM API key |
| `github-token` | Yes | - | GitHub token for API access |
| `lmnr-api-key` | No | `''` | Laminar API key for observability |

## A/B Testing Multiple Models

Test different LLM models by providing a comma-separated list:

```yaml
llm-model: 'anthropic/claude-sonnet-4-5-20250929,openai/gpt-4o,anthropic/claude-3-5-haiku-20241022'
```

One model is randomly selected for each review. When Laminar observability is enabled, the selected model is logged for comparison.

## Observability with Laminar

### Setting Up Laminar

1. Create a project at [Laminar](https://www.lmnr.ai/)
2. Copy your project API key
3. Add `LMNR_PROJECT_API_KEY` to your repository secrets
4. Uncomment the `lmnr-api-key` line in your workflow

### What Gets Traced

- **Review Trace**: Full agent execution including diff analysis, review generation, and comment posting
- **Metadata**: PR number, repository, review style, model used
- **Evaluation Trace**: (Optional) Created when PR is closed/merged to measure review effectiveness

### Review Evaluation

The evaluation workflow (`pr-review-evaluation.yml`) runs when PRs are closed and:
1. Downloads the review trace artifact
2. Fetches final PR state and comments
3. Creates an evaluation span in Laminar
4. Scores the review based on engagement metrics

### Laminar Dashboard

In your Laminar dashboard, you can:
- Filter traces by `pr-review` or `pr-review-evaluation` tags
- Compare review effectiveness across models (A/B testing)
- Analyze engagement metrics (human responses to agent comments)
- Set up signals for automated quality scoring

## Customizing Review Guidelines

Instead of forking the scripts, add custom guidelines to your repository:

### Option 1: Custom Code Review Skill

Create `.agents/skills/code-review.md`:

```markdown
---
name: code-review
description: Custom code review guidelines for my project
triggers:
- /codereview
---

# My Project Code Review Guidelines

You are a code reviewer for this project. Follow these guidelines:

## Review Focus
- Security vulnerabilities and data handling
- API contract compatibility
- Test coverage for new functionality

## Communication Style
- Be direct and constructive
- Use GitHub suggestion syntax for code fixes
```

### Option 2: Repository AGENTS.md

Add project-specific context to `AGENTS.md` at your repository root:

```markdown
# Project Context

This is a Python web application using FastAPI.

## Code Standards
- All public functions must have docstrings
- Use type hints for function signatures
- Follow PEP 8 style guidelines
```

## Migration from software-agent-sdk

If you were previously using workflows that referenced `OpenHands/software-agent-sdk`, update them to use this extensions repository:

**Before:**
```yaml
uses: OpenHands/software-agent-sdk/.github/actions/pr-review@main
```

**After:**
```yaml
uses: OpenHands/extensions/plugins/pr-review@main
```

Also update any `sdk-repo` and `sdk-version` inputs to `extensions-repo` and `extensions-version`.

## Troubleshooting

### Review Not Triggered

1. Check that the workflow file is in `.github/workflows/`
2. Verify the PR author association (automatic runs only for collaborators; otherwise a maintainer must trigger via label/reviewer request)
3. Ensure secrets are configured correctly

### Review Comments Not Appearing

1. Check the `GITHUB_TOKEN` has write permissions for pull requests
2. Review the workflow logs for API errors
3. Verify the LLM API key is valid

### Rate Limiting

If you see rate limit errors:
1. Reviews are automatically paginated to avoid limits
2. Consider using a dedicated bot token for high-volume repositories

## Security

- Uses `pull_request_target` to safely access secrets for fork PRs
- Automatic reviews only run for collaborators; manual triggers require **write (or higher)** permission
- PR code is checked out explicitly; secrets are not exposed to PR code
- Credentials are not persisted during checkout

## Contributing

See the main [extensions repository](https://github.com/OpenHands/extensions) for contribution guidelines.

## License

This plugin is part of the OpenHands extensions repository. See [LICENSE](../../LICENSE) for details.
