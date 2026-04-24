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
- **Unified Review Style**: Rigorous code review combining pragmatic engineering analysis with data structure and simplicity focus
- **A/B Testing**: Support for testing multiple LLM models
- **Review Context Awareness**: Considers previous reviews and unresolved threads
- **Evidence Enforcement**: Optional check that PR descriptions include concrete end-to-end proof the code works, not just test output
- **Sub-Agent Delegation**: Split large PR reviews across multiple sub-agents, one per file, then consolidate findings (see [Known Limitations](#known-limitations-sub-agent-delegation))
- **Observability**: Optional Laminar integration for tracing and evaluation

## Plugin Contents

```
plugins/pr-review/
├── README.md              # This file
├── action.yml             # Composite GitHub Action
├── skills/                # Symbolic links to review skills
│   ├── code-review -> ../../../skills/code-review
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
| `LLM_API_KEY` | Yes for `api-key` mode | API key for your LLM provider |
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

    # Default: API-key/LiteLLM auth
    # llm-auth-mode: api-key
    
    # Optional: Custom LLM endpoint
    # llm-base-url: https://your-llm-proxy.example.com
    
    # [DEPRECATED] review-style is no longer used; standard and roasted are merged
    # review-style: roasted

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

#### Experimental: ChatGPT subscription with device-code login

Use `llm-auth-mode: subscription` to authenticate through the OpenHands SDK's ChatGPT subscription support instead of an API key. Device-code login prints a URL and one-time code in the GitHub Actions log, then polls for up to 15 minutes while a human completes sign-in in a browser.

This mode is intended for manual experiments or persistent self-hosted runners. GitHub-hosted runners are ephemeral, so the first run requires human sign-in and any cached OAuth credentials are lost after the job ends.

```yaml
- name: Run PR Review
  uses: OpenHands/extensions/plugins/pr-review@main
  with:
    llm-auth-mode: subscription
    llm-subscription-auth-method: device_code
    llm-model: gpt-5.2-codex
    github-token: ${{ secrets.GITHUB_TOKEN }}

    # Temporary direct-reference example for unreleased SDK changes.
    # Remove this after the OpenHands SDK release includes device-code login.
    openhands-sdk-package: 'openhands-sdk @ git+https://github.com/OpenHands/software-agent-sdk.git@feat/openai-device-code-login#subdirectory=openhands-sdk'
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
| `llm-auth-mode` | No | `api-key` | LLM authentication mode: `api-key` or `subscription` |
| `llm-subscription-auth-method` | No | `device_code` | OpenAI subscription login method: `device_code` for remote/headless runners, or `browser` for local callback OAuth |
| `openhands-sdk-package` | No | `openhands-sdk` | Package spec passed to `uv --with`; use a direct-reference package spec to test unreleased SDK changes |
| `review-style` | No | `roasted` | **[DEPRECATED]** Previously chose between `standard` and `roasted` review styles. Now ignored — the styles have been merged into a single unified skill. |
| `require-evidence` | No | `'false'` | Require the reviewer to enforce an `Evidence` section in the PR description with end-to-end proof: screenshots/videos for frontend work, commands and runtime output for backend or scripts, and an agent conversation link when applicable. Test output alone does not qualify. |
| `use-sub-agents` | No | `'true'` | Enable sub-agent delegation for file-level reviews. The main agent acts as a coordinator that delegates per-file review work to `file_reviewer` sub-agents via the SDK TaskToolSet, then consolidates findings into a single PR review. Useful for large PRs with many changed files. To restore the previous single-agent behavior, set to `'false'`. |
| `extensions-repo` | No | `OpenHands/extensions` | Extensions repository |
| `extensions-version` | No | `main` | Git ref (tag, branch, or SHA) |
| `llm-api-key` | Yes for `api-key` mode | - | LLM API key |
| `github-token` | Yes | - | GitHub token for API access |
| `lmnr-api-key` | No | `''` | Laminar API key for observability |
| `enable-uv-cache` | No | `'false'` | Enable setup-uv's GitHub Actions cache for Python deps. Default `false` for security (see [Caching and Security](#caching-and-security)). |

## Caching and Security

Python dependency caching is **disabled by default**. `uv run --with ...` re-downloads OpenHands SDK and its transitive deps on every run, which is slow but safe.

**Why it's off by default:** Prompt injection can coerce the reviewer into executing arbitrary commands during the review. A compromised review run could write a malicious wheel into the shared GitHub Actions cache. Any later, higher-privilege workflow in the same repository that hits the same cache key would silently execute the attacker's code — a supply-chain pivot.

**Enabling it is safe when:**
- The runner is single-tenant (e.g. your own self-hosted runner, not shared with untrusted workflows).
- You do not run other privileged workflows in the same repository that would consume setup-uv's cache.
- You accept the residual risk in exchange for faster runs / lower disk writes.

**Self-hosted runners:** Consider mounting a host-level uv cache volume (e.g. `/home/runner/.cache` as a Docker volume) instead of — or in addition to — this option. A local volume is faster than a round trip to GHA cache storage and does not cross any trust boundary.

## Known Limitations: Sub-Agent Delegation

The following are known constraints of the sub-agent delegation feature. These are acceptable tradeoffs for the improved review depth it provides, and none pose a security risk — in the worst case a review may be less thorough than expected, which the single-agent fallback (`use-sub-agents: 'false'`) addresses.

- **LLM-driven JSON parsing**: The coordinator agent relies on the LLM to parse and merge JSON responses from sub-agents. There is no code-level validation of sub-agent output, so malformed responses may cause incomplete reviews.
- **Potential information loss during consolidation**: When merging findings from multiple sub-agents, the coordinator may lose or deduplicate findings imperfectly, especially for cross-file issues.
- **Sub-agents have read-only tools**: File reviewer sub-agents have access to `terminal` and `file_editor` for inspecting full source files and surrounding context, but they cannot query the GitHub API or post reviews — only the coordinator handles GitHub interaction.

To opt out, set `use-sub-agents: 'false'` in your workflow.

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

Create `.agents/skills/custom-codereview-guide.md`:

```markdown
---
name: custom-codereview-guide
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

Use a unique skill name (for example `custom-codereview-guide`) to **supplement** the default public `code-review` skill,
rather than overriding it. Keep `/codereview` as the trigger if you want this guidance applied in PR review runs.

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
2. Verify the PR author association (first-time contributors need manual trigger)
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

- Uses `pull_request_target` when you need secrets for fork PR reviews; apply strict maintainer-controlled triggers and checkout safeguards
- Keeps GitHub Actions caching disabled in privileged review workflows to avoid cache-poisoning pivots from prompt injection
- For lower-trust or comment-only smoke-test setups, prefer `pull_request` to reduce privilege by default
- Only triggers for trusted contributors or when maintainers add labels/reviewers
- PR code is checked out explicitly; secrets are not exposed to PR code
- Credentials are not persisted during checkout

## Contributing

See the main [extensions repository](https://github.com/OpenHands/extensions) for contribution guidelines.

## License

This plugin is part of the OpenHands extensions repository. See [LICENSE](../../LICENSE) for details.
