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
- **Evidence Enforcement**: Optional check that PR descriptions include concrete end-to-end proof the code works, not just test output
- **Observability**: Optional Laminar integration for tracing and evaluation

## How It Works

The PR review workflow uses the OpenHands Software Agent SDK to analyze your code changes:

1. **Trigger**: The workflow runs when a PR is opened, marked ready, labeled, or when a reviewer is requested
2. **Analysis**: The agent receives the complete PR diff and uses skills from this repository:
   - **`/codereview`** or **`/codereview-roasted`**: Analyzes code for quality, security, and best practices
   - **`/github-pr-review`**: Posts structured inline comments via the GitHub API
3. **Output**: Review comments are posted directly on the PR with priority labels (🔴 Critical, 🟠 Important, 🟡 Suggestion, 🟢 Nit) and actionable suggestions

### Composite Action

This plugin uses a reusable composite GitHub Action that handles all the setup automatically:

- **Checkout**: Downloads both the extensions repository and your PR code
- **Environment Setup**: Installs Python 3.12, uv, and GitHub CLI
- **Dependencies**: Uses `uv run` to install openhands-sdk, openhands-tools, and lmnr on-demand
- **Execution**: Runs the PR review agent script with your configuration
- **Artifacts**: Uploads logs and trace information for debugging and evaluation

The composite action approach means you don't need to maintain the workflow logic in your repository—just reference the action and provide your configuration.

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

    # Optional: require an Evidence section proving the code works end-to-end
    # require-evidence: 'true'
    
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

1. A new non-draft PR is opened (by non-first-time contributors)
2. A draft PR is marked as ready for review
3. The `review-this` label is added
4. `openhands-agent` or `all-hands-bot` is requested as a reviewer

### Requesting a Review

**Option 1: Request as Reviewer (Recommended)**
1. Open the PR
2. Click **Reviewers** in the sidebar
3. Select `openhands-agent` as a reviewer

**Option 2: Add Label**
1. Open the PR
2. Add the `review-this` label

## Action Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `llm-model` | No | `anthropic/claude-sonnet-4-5-20250929` | LLM model(s), comma-separated for A/B testing |
| `llm-base-url` | No | `''` | Custom LLM endpoint URL |
| `review-style` | No | `roasted` | Review style: `standard` or `roasted` |
| `require-evidence` | No | `'false'` | Require the reviewer to enforce an `Evidence` section in the PR description with end-to-end proof: screenshots/videos for frontend work, commands and runtime output for backend or scripts, and an agent conversation link when applicable. Test output alone does not qualify. |
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

Instead of forking the scripts, you can customize the code review behavior by adding repository-specific guidelines. This is the **recommended approach** for customization.

### How Skill Overriding Works

The PR review agent uses skills from the [OpenHands/extensions](https://github.com/OpenHands/extensions) repository by default. When you add a `.agents/skills/code-review.md` file to your repository, it **overrides** the default skill with your custom guidelines.

This means you can:
- Keep using the official action without forking
- Maintain your review standards in version control
- Update your guidelines without waiting for upstream changes
- Ensure consistent reviews across your team

### Option 1: Custom Code Review Skill

Create `.agents/skills/code-review.md` in your repository:

```markdown
---
name: code-review
description: Custom code review guidelines for my project
triggers:
- /codereview
---

# My Project Code Review Guidelines

You are a code reviewer for this project. Follow these guidelines:

## Review Decisions

- **APPROVE** straightforward changes (config updates, typo fixes, documentation)
- **COMMENT** when you have feedback or concerns

## What to Check

- Code follows our project conventions
- Tests are included for new functionality
- No security vulnerabilities introduced
- Documentation is updated if needed

## Communication Style

- Be direct and constructive
- Use GitHub suggestion syntax for code fixes
- Approve quickly when code is good
```

**Important**: The skill file must use `/codereview` as the trigger (in the frontmatter) to override the default review behavior.

**Reference Example**: See the [OpenHands Software Agent SDK's code-review skill](https://github.com/OpenHands/software-agent-sdk/blob/main/.agents/skills/code-review.md) for a comprehensive example.

### Option 2: Repository AGENTS.md

Add project-specific context to `AGENTS.md` at your repository root. This provides additional context without replacing the default review skill:

```markdown
# Project Context

This is a Python web application using FastAPI.

## Code Standards
- All public functions must have docstrings
- Use type hints for function signatures
- Follow PEP 8 style guidelines

## Testing Requirements
- Unit tests required for all new features
- Integration tests for API endpoints
- Minimum 80% code coverage
```

The agent will consider both the skill guidelines and your AGENTS.md context when reviewing code.

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

## Example Reviews

See real automated reviews in action from the OpenHands Software Agent SDK repository:

| PR | Description | Review Highlights |
|---|---|---|
| [#1927](https://github.com/OpenHands/software-agent-sdk/pull/1927#pullrequestreview-3767493657) | Composite GitHub Action refactor | Comprehensive review with 🔴 Critical, 🟠 Important, and 🟡 Suggestion labels |
| [#1916](https://github.com/OpenHands/software-agent-sdk/pull/1916#pullrequestreview-3758297071) | Add example for reconstructing messages | Critical issues flagged with clear explanations |
| [#1904](https://github.com/OpenHands/software-agent-sdk/pull/1904#pullrequestreview-3751821740) | Update code-review skill guidelines | APPROVED review highlighting key strengths |
| [#1889](https://github.com/OpenHands/software-agent-sdk/pull/1889#pullrequestreview-3747576245) | Fix tmux race condition | Technical review of concurrency fix with dual-lock strategy analysis |

These examples demonstrate:
- **Inline comments** on specific lines of code
- **Priority labeling** (🔴 Critical, 🟠 Important, 🟡 Suggestion, 🟢 Nit)
- **Actionable feedback** with code examples and suggestions
- **Context-aware analysis** considering the broader codebase

## Troubleshooting

### Review Not Triggered

**Symptoms**: Workflow doesn't start when you expect it to

**Solutions**:
1. **Check workflow file location**: Ensure the workflow file is in `.github/workflows/` directory
2. **Verify PR author association**: First-time contributors (`FIRST_TIME_CONTRIBUTOR` or `NONE` association) require manual trigger via label or reviewer request for security
3. **Check secrets**: Verify `LLM_API_KEY` is set in repository settings under **Settings → Secrets and variables → Actions**
4. **Review trigger conditions**: Check the `if:` condition in your workflow matches your intended trigger events
5. **Check Actions tab**: Look for workflow run errors in the **Actions** tab of your repository

### Review Comments Not Appearing

**Symptoms**: Workflow runs successfully but no comments appear on the PR

**Solutions**:
1. **Check permissions**: Ensure your workflow has these permissions:
   ```yaml
   permissions:
     contents: read
     pull-requests: write
     issues: write
   ```
2. **Verify GITHUB_TOKEN**: For fork PRs, ensure you're using `pull_request_target` (not `pull_request`)
3. **Check workflow logs**: Look for GitHub API errors in the workflow execution logs
4. **Validate LLM API key**: Test that your `LLM_API_KEY` is valid and has available quota
5. **Review rate limits**: Check if you've hit GitHub API rate limits (rare with default tokens)

### Review Taking Too Long

**Symptoms**: Review runs for more than 5-10 minutes

**Solutions**:
1. **Large PRs**: PRs with many files or large diffs take longer to analyze
   - Consider splitting large PRs into smaller, focused changes
   - The agent truncates very large diffs (>100,000 characters) automatically
2. **LLM API delays**: Check if your LLM provider is experiencing slowdowns
3. **Check concurrency**: The workflow uses concurrency control to cancel previous runs when new commits are pushed

### Rate Limiting

**Symptoms**: GitHub API rate limit errors in logs

**Solutions**:
1. Reviews are automatically paginated to avoid limits on fetching review history
2. For high-volume repositories, consider using a dedicated bot token (e.g., `ALLHANDS_BOT_GITHUB_PAT`) instead of the default `GITHUB_TOKEN`
3. GitHub's rate limits reset hourly—you can wait and retry

### Agent Not Using Custom Skill

**Symptoms**: Agent ignores your `.agents/skills/code-review.md` file

**Solutions**:
1. **Check file location**: File must be at `.agents/skills/code-review.md` (note the dot prefix)
2. **Verify frontmatter**: Ensure the YAML frontmatter includes `triggers: [/codereview]`
3. **Review file syntax**: Make sure the markdown is valid and frontmatter is properly formatted
4. **Check workflow logs**: Look for skill loading messages in the agent execution logs

## Security

### Why `pull_request_target`?

This workflow uses `pull_request_target` instead of `pull_request` so the code review agent can access secrets and post comments on PRs from forks. The workflow runs in the context of the base repository (not the fork), which provides access to repository secrets.

### Security Safeguards

1. **Trusted Contributors Only**: The workflow automatically runs for non-first-time contributors. First-time contributors require a maintainer to manually add the `review-this` label or request a review.

2. **Explicit Checkout**: The PR code is explicitly checked out in a separate directory (`pr-repo/`) and is not automatically trusted.

3. **No Credential Persistence**: The checkout uses `persist-credentials: false` to prevent git credentials from being stored.

4. **SDK Secret Masking**: API keys are passed as SDK secrets rather than plain environment variables, which provides automatic masking in logs and prevents the agent from directly accessing these credentials during code execution.

### Potential Risk

⚠️ **Important**: A malicious contributor could submit a PR containing code designed to exfiltrate your `LLM_API_KEY` when the review agent analyzes their code.

**Mitigation**: The PR review workflow passes API keys as SDK secrets, which are:
- Automatically masked in all agent output and logs
- Not directly accessible as environment variables during agent execution
- Only used internally by the SDK for LLM API calls

For more details on how SDK secrets work, see the [SDK Secrets documentation](https://docs.openhands.dev/sdk/guides/secrets).

### Caching Strategy

This action uses `uv` with caching enabled to speed up dependency installation. GitHub Actions caches are scoped to the repository and branch, providing isolation between different PRs and preventing cache poisoning attacks.

## Related Resources

- **[OpenHands Extensions Repository](https://github.com/OpenHands/extensions)** - Source code for this plugin and other OpenHands extensions
- **[Code Review Skills](https://github.com/OpenHands/extensions/tree/main/skills/code-review)** - Default review skills used by the agent
- **[PR Review Action](https://github.com/OpenHands/extensions/blob/main/plugins/pr-review/action.yml)** - Composite GitHub Action implementation
- **[Software Agent SDK](https://docs.openhands.dev/sdk)** - Build your own AI-powered workflows
- **[SDK Secrets Guide](https://docs.openhands.dev/sdk/guides/secrets)** - Learn about secure credential handling
- **[Skills Documentation](https://docs.openhands.dev/overview/skills)** - Learn more about OpenHands skills
- **[OpenHands Cloud GitHub Integration](https://docs.openhands.dev/openhands/usage/cloud/github-installation)** - Alternative: Use OpenHands Cloud for PR reviews

## Contributing

See the main [extensions repository](https://github.com/OpenHands/extensions) for contribution guidelines.

## License

This plugin is part of the OpenHands extensions repository. See [LICENSE](../../LICENSE) for details.
