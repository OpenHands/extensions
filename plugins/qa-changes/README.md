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

The QA agent follows a five-phase methodology:

1. **Understand** — Reads the PR diff, title, and description. Classifies changes as new features, bug fixes, refactors, or config/docs.
2. **Setup** — Bootstraps the repo: installs dependencies, builds the project, establishes a test baseline.
3. **Test** — Runs the existing test suite. Records pass/fail counts and detects regressions.
4. **Exercise** — Goes beyond the test suite: manually executes new features, reproduces fixed bugs, verifies edge cases.
5. **Report** — Posts a structured QA report as a PR comment with evidence (commands, outputs) and a verdict (PASS / PASS WITH ISSUES / FAIL).

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

### Test Suite Results
[Pass/fail counts, regressions]

### Functional Verification
[Commands run, outputs observed, behavior verified]

### Issues Found
- 🔴 **Blocker**: [Description]
- 🟠 **Issue**: [Description]
- 🟡 **Minor**: [Description]

### Verdict
✅ PASS / ⚠️ PASS WITH ISSUES / ❌ FAIL
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

The workflow uses `pull_request_target` so the QA agent can access secrets for fork PRs. Only users with write access can trigger QA via labels or reviewer requests.

**Note**: The QA agent executes code from the PR. Only trigger it on PRs you trust. The `FIRST_TIME_CONTRIBUTOR` and `NONE` author associations are excluded from automatic triggers — use the label or reviewer request for those.

## Contributing

See the main [extensions repository](https://github.com/OpenHands/extensions) for contribution guidelines.

## License

This plugin is part of the OpenHands extensions repository. See [LICENSE](/LICENSE) for details.
