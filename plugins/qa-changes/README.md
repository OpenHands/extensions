# QA Changes Plugin

Automated pull request QA validation using OpenHands agents. Unlike the [PR Review plugin](../pr-review/) which reads diffs and posts code review comments, this plugin **actually runs the code** — setting up the environment, executing the test suite, exercising changed behavior, and posting a structured QA report.

## Quick Start

Copy the workflow file to your repository:

```bash
cp plugins/qa-changes/workflows/qa-changes-by-openhands.yml \
   .github/workflows/qa-changes-by-openhands.yml
```

Then configure the required secrets (see [Installation](#installation) below).

## How It Works

The QA agent follows a four-phase methodology:

1. **Understand** — Reads the PR diff, title, and description. Classifies changes and identifies entry points (CLI commands, API endpoints, UI pages).
2. **Setup** — Bootstraps the repo: installs dependencies, builds the project. Checks CI status and only runs tests CI does not cover.
3. **Exercise** — The core phase. Actually uses the software the way a human would: spins up servers, opens browsers, runs CLI commands, makes HTTP requests. The bar is high — "tests pass" is not enough.
4. **Report** — Posts a structured QA report as a PR comment with evidence (commands, outputs, screenshots) and a verdict.

The agent knows when to give up: if a verification approach fails after three materially different attempts, it switches to a different approach. If two fundamentally different approaches fail, it reports honestly what could not be verified and suggests `AGENTS.md` guidance for future runs.

## Plugin Contents

```
plugins/qa-changes/
├── README.md              # This file
├── action.yml             # Composite GitHub Action
├── skills/                # Symbolic links to QA skills
│   └── qa-changes -> ../../../skills/qa-changes
├── workflows/             # Example GitHub workflow files
│   └── qa-changes-by-openhands.yml
└── scripts/               # Python scripts for QA execution
    ├── agent_script.py    # Main QA agent script
    └── prompt.py          # Prompt template
```

## Installation

### 1. Copy the Workflow File

Copy the workflow file to your repository's `.github/workflows/` directory:

```bash
mkdir -p .github/workflows
cp plugins/qa-changes/workflows/qa-changes-by-openhands.yml \
   .github/workflows/qa-changes-by-openhands.yml
```

### 2. Configure Secrets

Add the following secrets in your repository settings (**Settings → Secrets and variables → Actions**):

| Secret | Required | Description |
|--------|----------|-------------|
| `LLM_API_KEY` | Yes | API key for your LLM provider |
| `GITHUB_TOKEN` | Auto | Provided automatically by GitHub Actions |

### 3. Create the QA Label (Optional)

Create a `qa-this` label for manual QA triggers:

1. Go to **Issues → Labels**
2. Click **New label**
3. Name: `qa-this`
4. Description: `Trigger OpenHands QA validation`

## Usage

### Automatic Triggers

QA validation is automatically triggered when:
- A new non-draft PR is opened (by trusted contributors)
- A draft PR is marked as ready for review
- The `qa-this` label is added
- `openhands-agent` is requested as a reviewer

### Requesting QA

**Option 1: Add Label**

Add the `qa-this` label to any PR.

**Option 2: Request as Reviewer**

Request `openhands-agent` as a reviewer on the PR.

## Action Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `llm-model` | No | `anthropic/claude-sonnet-4-5-20250929` | LLM model to use |
| `llm-base-url` | No | `''` | Custom LLM endpoint URL |
| `extensions-repo` | No | `OpenHands/extensions` | Extensions repository |
| `extensions-version` | No | `main` | Git ref (tag, branch, or SHA) |
| `llm-api-key` | Yes | - | LLM API key |
| `github-token` | Yes | - | GitHub token for API access |

## QA Report Format

The agent posts a PR comment with this structure:

```
## QA Report

**Summary**: [One-sentence verdict]

### Environment Setup
[Build/install results]

### CI & Test Status
[CI check results, any additional tests run beyond CI]

### Functional Verification
[Commands run, outputs observed, screenshots, behavior verified]

### Unable to Verify (if applicable)
[What could not be verified, what was attempted, suggested AGENTS.md guidance]

### Issues Found
- 🔴 **Blocker**: [Description]
- 🟠 **Issue**: [Description]
- 🟡 **Minor**: [Description]

### Verdict
✅ PASS / ⚠️ PASS WITH ISSUES / ❌ FAIL / 🟡 PARTIAL
```

## Customizing QA Guidelines

Add project-specific QA guidelines to your repository:

### Option 1: Custom QA Skill

Create `.agents/skills/qa-guide.md`:

```markdown
---
name: qa-guide
description: Project-specific QA guidelines
triggers:
- /qa-changes
---

# Project QA Guidelines

## Setup Commands
- `make install` to install dependencies
- `make build` to build the project

## Test Commands
- `make test` for unit tests
- `make test-integration` for integration tests

## Key Behaviors to Verify
- [List critical user flows]
- [List known fragile areas]
```

### Option 2: Repository AGENTS.md

Add setup and test commands to `AGENTS.md` at your repository root. The agent reads this file automatically.

## Security

The workflow uses `pull_request` (not `pull_request_target`) so that fork PRs do **not** get access to the base repository's secrets. Since the QA agent *executes* code from the PR (unlike a code-review agent which only reads diffs), using `pull_request_target` would allow untrusted fork code to run with the repo's `GITHUB_TOKEN` and `LLM_API_KEY`.

The trade-off is that fork PRs won't have access to repository secrets and the QA workflow won't run for them. Maintainers can run QA locally or set up a separate trusted workflow for those cases.

**Note**: The `FIRST_TIME_CONTRIBUTOR` and `NONE` author associations are excluded from automatic triggers as an additional safety layer.

## Contributing

See the main [extensions repository](https://github.com/OpenHands/extensions) for contribution guidelines.

## License

This plugin is part of the OpenHands extensions repository. See [LICENSE](/LICENSE) for details.
