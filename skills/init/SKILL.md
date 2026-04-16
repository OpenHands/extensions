---
name: init
description: >-
  Initialize and onboard a repository for AI-assisted development. Quick mode
  (/init): scaffold an AGENTS.md contributor guide. Full setup
  (setup-openhands): create AGENTS.md, bootstrap scripts, and PR review
  workflow. Also includes agent readiness assessment and improvement workflows.
triggers:
- /init
- setup-openhands
- setup-agents-md
- agent-readiness-report
- improve-agent-readiness
- setup-pr-review
---

# Repository Initialization & Onboarding

This skill covers the full spectrum of getting a repository ready for AI agents,
from a quick AGENTS.md scaffold to a comprehensive agent-readiness assessment.

## Quick Start — `/init`

Use `/init` when you just need an `AGENTS.md` file fast.

### Target path rules

- `/init`: create `AGENTS.md` at the repository root.
- `/init <path>`: create `AGENTS.md` scoped to `<path>`.
  - If `<path>` is a directory, write `<path>/AGENTS.md`.
  - If `<path>` ends with `.md`, treat it as the full output file path.

Never overwrite an existing file silently. If the target file already exists,
ask the user whether to (a) keep it, (b) edit it, or (c) replace it.

### Quick init workflow

1. **Inspect the repo to tailor the guide**
   - Skim top-level structure (`ls`, `find -maxdepth 2`).
   - Read the primary docs (`README*`, `CONTRIBUTING*`, `DEVELOPMENT*`, `Makefile`).
   - Identify build tooling and common commands (`pyproject.toml`, `package.json`, CI configs).
   - Locate tests and how they are run (`tests/`, workflow YAMLs, task runners).

2. **Write a concise `AGENTS.md`** using the spec below.

3. **Create the file** at the target location.

### `AGENTS.md` spec

- Title the document: `# Repository Guidelines`.
- Use Markdown headings (`##`) to organize sections.
- Keep it concise: **200–400 words**.
- Keep explanations short, direct, and specific to the repo.
- Prefer concrete examples (commands, directory paths, naming patterns).

#### Recommended sections (adapt as needed)

- Project Structure & Module Organization
- Build, Test, and Development Commands
- Coding Style & Naming Conventions
- Testing Guidelines
- Commit & Pull Request Guidelines
- Optional: Security & Configuration Tips, Architecture Overview, Agent-specific instructions

### Content guidelines

- Only include information that's broadly useful for future tasks (avoid one-off issue details).
- If the repo already contains nested `AGENTS.md` files, briefly mention that more deeply nested files override broader ones within their directory tree.

---

## Deep AGENTS.md — `setup-agents-md`

Use this when you want a thorough, high-quality AGENTS.md that extracts real
commands, structure, conventions, and guardrails from the repository.

### Why this matters

An AGENTS.md is the single highest-impact addition for agent readiness. Without
it, agents guess at build commands, miss project conventions, run the wrong test
suite, and don't know what's dangerous.

### Step 0: Check for an existing AGENTS.md

Look for an existing `AGENTS.md` (or `.agents/AGENTS.md`) in the repo root.
If one exists, **do not rewrite it from scratch**. Instead, read the repo,
compare what you find against what's already documented, and suggest specific
additions or changes. Present the suggestions to the user and let them decide.

### Step 1: Read the repo

Before writing anything, gather the actual information:

**Commands** (most important — agents need to know how to build, test, lint):
- `Makefile` / `justfile` / `Taskfile.yml` — build/test/lint/format targets
- `package.json` `scripts` — npm/yarn/pnpm run targets
- `pyproject.toml` — Python tooling config
- `.github/workflows/*.yml` — CI steps reveal the real commands
- `Cargo.toml`, `build.gradle` / `pom.xml`, `Rakefile`, `docker-compose.yml`

**Project structure**: top-level directory listing, monorepo indicators, source vs test layout.

**Conventions**: linter/formatter configs, CONTRIBUTING.md, existing README, `.editorconfig`.

**Guardrails**: database configs (destructive commands), CI enforcement, secrets/env patterns, branch protection.

### Step 2: Write the AGENTS.md

Use this structure (include only what's relevant):

```markdown
# AGENTS.md

## Project overview
One or two sentences: what this project is, language/framework, high-level architecture.

## Commands
### Build
### Test
### Lint & format

## Project structure
What's in each top-level directory.

## Coding standards
Language-specific conventions not captured by linter config.

## Testing
Where tests live, how to run single test vs full suite, test DB setup.

## Guardrails
Things the agent must NOT do. Destructive commands, files not to edit by hand.
```

### Key principles

- **Be specific, not generic.** Write `uv run ruff check --fix <file>`, not "run the linter."
- **Commands are king.** Every command block should be copy-pasteable.
- **Link, don't repeat.** Reference CONTRIBUTING.md or architecture docs by path.
- **Include dangerous operations.** If `make db-reset` destroys the dev database, say so.
- **Keep it maintainable.** Short and accurate beats long and generic.

---

## Full Setup — `setup-openhands`

Use this when you want to fully configure a repository for OpenHands, including
AGENTS.md, bootstrap scripts, and PR review workflow.

### Step 1: Create AGENTS.md

Run the deep `setup-agents-md` workflow above to generate a root-level AGENTS.md
from the repo's actual CI workflows, build files, and documentation.

### Step 2: Create `.openhands/setup.sh`

Create a bootstrap script that runs at the start of every OpenHands session.
Read the repo's CI workflows, AGENTS.md, and build files to determine correct
commands. The script should:

- Install dependencies (the project's actual install command)
- Set required environment variables
- Run any other bootstrap steps (e.g. copy `.env.example` to `.env`)

Keep it idempotent and fast. Use real commands from CI, not generic examples.

**Docs**: https://docs.openhands.dev/openhands/usage/customization/repository#setup-script

### Step 3: Create `.openhands/pre-commit.sh`

Create a pre-commit script that runs before every commit OpenHands makes.
Mirror the lint and test commands from CI. Exit non-zero on failure so the
agent gets immediate feedback instead of waiting for CI.

**Docs**: https://docs.openhands.dev/openhands/usage/customization/repository#pre-commit-script

### Step 4: Set up PR review

Run the `setup-pr-review` workflow below to create the GitHub Actions workflow
and walk the user through configuration.

### Step 5: Verify

Confirm all files exist and are correct:
- `AGENTS.md` at repo root with real commands (not boilerplate)
- `.openhands/setup.sh` with the project's actual install/bootstrap commands
- `.openhands/pre-commit.sh` mirroring the CI lint/test checks
- `.github/workflows/pr-review.yml` with valid YAML

---

## Set Up PR Review — `setup-pr-review`

Add the PR review workflow to a GitHub repository so an OpenHands agent can
review pull requests and post inline comments.

**Docs**: https://docs.all-hands.dev/sdk/guides/github-workflows/pr-review

### Step 1: Create the workflow file

Create `.github/workflows/pr-review.yml`. Fetch the latest example from the
docs and use it as the starting template.

### Step 2: Configure the LLM

Ask the user whether they use the **OpenHands app** or their **own LLM provider**.

**OpenHands app**: Tell them to get an LLM key from
https://app.all-hands.dev → Account → API Keys → OpenHands LLM Key, add it as
a GitHub secret named `LLM_API_KEY`. Set `llm-model: litellm_proxy/claude-sonnet-4-5-20250929`
and `llm-base-url: https://llm-proxy.app.all-hands.dev`.

**Own LLM provider**: Add their API key as `LLM_API_KEY` secret. Set `llm-model`
to the provider-prefixed model name (e.g. `anthropic/claude-sonnet-4-5-20250929`).

**You cannot create secrets — the user must do it manually.**

### Step 3: Ask the user for preferences

- **Review style**: `roasted` (blunt, Torvalds-style) or `standard` (balanced)
- **When to trigger**: on-demand (add `review-this` label or request reviewer) or automatic (every new PR)

---

## Agent Readiness Report — `agent-readiness-report`

Evaluate how well a repository supports autonomous AI-assisted development
across five pillars covering 74 features.

### Five Pillars

| Pillar | Question | Features |
|--------|----------|----------|
| **Agent Instructions** | Does the agent know what to do? | 18 |
| **Feedback Loops** | Does the agent know if it's right? | 16 |
| **Workflows & Automation** | Does the process support agent work? | 15 |
| **Policy & Governance** | Does the agent know the rules? | 13 |
| **Build & Dev Environment** | Can the agent build and run the project? | 12 |

See `references/criteria.md` for the full list with descriptions and evidence.

### How to run

#### Step 1: Run the scanner scripts

```bash
for s in scripts/scan_*.sh; do bash "$s" /path/to/repo; echo; done
```

The scripts find files and patterns but do not evaluate quality. Many features
require reading the actual files to assess.

#### Step 2: Evaluate each feature

Walk through `references/criteria.md` pillar by pillar. Mark each feature:
**✓** (present), **✗** (missing), or **—** (not applicable).

#### Step 3: Write the report

```
# Agent Readiness Report: {repo name}

## Summary
- Features present: X / 74
- Strongest pillar: {pillar}
- Weakest pillar: {pillar}

## Pillar 1 · Agent Instructions (X / 18)
✓ Agent instruction file — AGENTS.md at root
✗ Multi-model support — only Cursor configured
...
```

---

## Improve Agent Readiness — `improve-agent-readiness`

Take a readiness report and turn its gaps into concrete, repo-appropriate fixes.

### Prerequisites

This expects an agent readiness report to already exist — either from running
`agent-readiness-report` or provided by the user.

### Step 1: Read the report

Identify every **✗** (missing) feature across all five pillars.

### Step 2: Propose high-impact fixes

Pick the **5–10 changes that would help agents the most**, ranked by impact:

1. Things that unblock agents from working at all (AGENTS.md, build commands,
   bootstrap scripts, dev environment setup)
2. Things that give agents faster feedback (pre-commit hooks, test docs, PR templates)
3. Things that improve quality or process (CI caching, label automation)
4. Things that improve governance or compliance (SECURITY.md, CODEOWNERS)

Proposals should fit the specific repo — look at languages, frameworks, tools,
and existing conventions.

### Step 3: Implement on request

When the user approves fixes, implement them, then update the readiness report
to reflect the new state. Follow these rules:

- **Don't generate boilerplate** — content should be specific to this repo
- **Match existing style** — if the repo uses tabs, use tabs
- **Don't over-generate** — concise and accurate beats long and generic
- **Commit atomically** — one commit per logical fix

## References

- Agent readiness criteria (74 features): `references/criteria.md`
