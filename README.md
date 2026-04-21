# OpenHands Extensions

This repository is the **public extensions registry** for [OpenHands](https://github.com/OpenHands/OpenHands).
It contains reusable, shareable skills and plugins that customize agent behavior.

- Skills overview docs: https://docs.openhands.dev/overview/skills
- SDK skill guide: https://docs.openhands.dev/sdk/guides/skill

## Repository Layout

### Skills

Skills are Markdown-based guidelines that provide domain-specific knowledge and instructions.
They live under `skills/`, **one directory per skill**:

- `skills/<skill-name>/SKILL.md` — the skill definition (AgentSkills-style progressive disclosure)
- `skills/<skill-name>/README.md` — optional human-facing notes/examples

Browse the catalog in [`skills/`](skills/).

### Plugins

Plugins are extensions with executable code components (hooks, scripts).
They live under `plugins/`, **one directory per plugin**:

- `plugins/<plugin-name>/SKILL.md` — the plugin definition
- `plugins/<plugin-name>/hooks/` — lifecycle hooks
- `plugins/<plugin-name>/scripts/` — utility scripts

Browse available plugins in [`plugins/`](plugins/).

## Extensions Catalog

<!-- BEGIN AUTO-GENERATED CATALOG -->
This repository contains **2 marketplace(s)** with **46 extensions** (37 skills, 9 plugins).

### Quick Start

**OpenHands CLI / GUI / Cloud** — these skills are loaded automatically. No setup needed.

**OpenHands SDK** — enable public skills when creating your agent context:

```python
from openhands.sdk import AgentContext

agent_context = AgentContext(load_public_skills=True)
```

Or load them explicitly with `load_public_skills()` from `openhands.sdk.context.skills`.

<details>
<summary><strong>Using Claude Code?</strong></summary>

This repository is also a [Claude Code plugin marketplace](https://code.claude.com/docs/en/discover-plugins). To add it:

1. Start Claude Code:
   ```
   claude
   ```
2. Add the marketplace:
   ```
   /plugin marketplace add OpenHands/extensions
   ```
3. Install the plugins you want:
   ```
   /plugin install
   ```
4. Reload to activate:
   ```
   /reload-plugins
   ```

</details>

### large-codebase

OpenHands skills for interacting, improving, and refactoring large codebases

**4 extensions** (2 skills, 2 plugins)

| Name | Type | Description | Commands |
|------|------|-------------|----------|
| add-javadoc | skill | Add comprehensive JavaDoc documentation to Java classes and methods. Use when documenting Java code, adding API docum... | — |
| cobol-modernization | plugin | End-to-end COBOL to Java migration workflow. Handles build setup, mainframe dependency removal, and code migration wi... | — |
| migration-scoring | plugin | Evaluate code migration quality with coverage, correctness, and style scoring. Generates executive reports with actio... | — |
| spark-version-upgrade | skill | Upgrade Apache Spark applications between major versions (2.x→3.x, 3.x→4.x). Covers build files, deprecated APIs, con... | — |

### openhands-extensions

Official skills and plugins for OpenHands — the open-source AI software engineer.

**42 extensions** (35 skills, 7 plugins)

| Name | Type | Description | Commands |
|------|------|-------------|----------|
| add-skill | skill | Add (import) an OpenHands skill from a GitHub repository into the current workspace. | — |
| agent-creator | skill | Create file-based sub-agents as Markdown files — no Python code required. Guides the user through a structured interv... | `/agent-creator` |
| agent-memory | skill | Persist and retrieve repository-specific knowledge using AGENTS.md files. Use when you want to save important informa... | `/remember` |
| agent-sdk-builder | skill | Guided workflow for building custom AI agents using the OpenHands Software Agent SDK. Use when you want to create a n... | `/agent-builder` |
| automation | skill | Create and manage OpenHands automations - scheduled tasks that run in sandboxes. Use the prompt preset to create auto... | — |
| automation-creation | plugin | Interactive slash command for creating OpenHands automations from a natural language prompt. Provides /automation:cre... | — |
| azure-devops | skill | Interact with Azure DevOps repositories, pull requests, and APIs using the AZURE_DEVOPS_TOKEN environment variable. U... | — |
| bitbucket | skill | Interact with Bitbucket repositories and pull requests using the BITBUCKET_TOKEN environment variable. Use when worki... | — |
| city-weather | plugin | Get current weather, time, and precipitation forecast for any city using the free Open-Meteo API. Provides slash comm... | — |
| code-review | skill | Rigorous code review focusing on data structures, simplicity, security, pragmatism, and risk/safety evaluation. Provi... | `/codereview`, `/codereview-roasted` |
| datadog | skill | Query and analyze Datadog logs, metrics, APM traces, and monitors using the Datadog API. Use when debugging productio... | — |
| deno | skill | Common project operations using Deno (tasks, run/test/lint/fmt, and dependency management). | — |
| discord | skill | Build and automate Discord integrations (bots, webhooks, slash commands, and REST API workflows). Use when the user m... | — |
| docker | skill | Run Docker commands within a container environment, including starting the Docker daemon and managing containers. Use... | — |
| flarglebargle | skill | A test skill that responds to the magic word 'flarglebargle' with a compliment. Use for testing skill activation and ... | — |
| frontend-design | skill | Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks ... | — |
| github | skill | Interact with GitHub repositories, pull requests, issues, and workflows using the GITHUB_TOKEN environment variable a... | — |
| github-pr-review | skill | Post structured PR reviews to GitHub with inline comments/suggestions in a single API call. | `/github-pr-review` |
| gitlab | skill | Interact with GitLab repositories, merge requests, and APIs using the GITLAB_TOKEN environment variable. Use when wor... | — |
| init | skill | Scaffold an AGENTS.md contributor guide for a repository or subdirectory. | `/init` |
| iterate | skill | Iterate on a GitHub pull request — drive it through CI, code review, and QA until merge-ready. Monitors state, fixes ... | `/iterate`, `/verify`, `/babysit` |
| jupyter | skill | Read, modify, execute, and convert Jupyter notebooks programmatically. Use when working with .ipynb files for data sc... | — |
| kubernetes | skill | Set up and manage local Kubernetes clusters using KIND (Kubernetes IN Docker). Use when testing Kubernetes applicatio... | — |
| learn-from-code-review | skill | Distill code review feedback from GitHub PRs into reusable skills and guidelines. Use when users ask to learn from co... | `/learn-from-reviews` |
| linear | skill | Interact with Linear project management - query issues, update status, create tickets using the Linear GraphQL API. | — |
| magic-test | plugin | A simple test plugin for verifying plugin loading. Triggers on magic words (alakazam, abracadabra) and returns a spec... | — |
| notion | skill | Create, search, and update Notion pages/databases using the Notion API. Use for documenting work, generating runbooks... | — |
| npm | skill | Handle npm package installation in non-interactive environments by piping confirmations. Use when installing Node.js ... | — |
| onboarding | plugin | Assess repository agent-readiness across five pillars, propose high-impact fixes, and generate repo-specific AGENTS.m... | — |
| openhands-api | skill | Use the OpenHands Cloud REST API (V1) to create and manage app conversations, including multi-conversation delegation... | — |
| pdflatex | skill | Install and use pdflatex to compile LaTeX documents into PDFs on Linux. Use when generating academic papers, research... | — |
| pr-review | plugin | Automated PR code review — analyzes diffs and posts inline review comments via the GitHub API. | — |
| prd | skill | Generate a Product Requirements Document (PRD) for a new feature through an interactive clarifying-question workflow.... | `/prd` |
| release-notes | plugin | Generate consistent, well-structured release notes from git history. Produces categorized changelog with breaking cha... | `/release-notes` |
| security | skill | Security best practices for secure coding, authentication, authorization, and data protection. Use when developing fe... | — |
| skill-creator | skill | Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an ex... | — |
| ssh | skill | Establish and manage SSH connections to remote machines, including key generation, configuration, and file transfers.... | — |
| swift-linux | skill | Install and configure Swift programming language on Debian Linux for server-side development. Use when building Swift... | — |
| theme-factory | skill | Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reportings, HTML landing pages, etc.... | — |
| uv | skill | Common project, dependency, and environment operations using uv. | — |
| vercel | skill | Deploy and manage applications on Vercel, including preview deployments and deployment protection. | — |
| vulnerability-remediation | plugin | Automated security vulnerability scanning and AI-powered remediation. Scans repositories, skips when no issues found,... | — |
<!-- END AUTO-GENERATED CATALOG -->

## Contributing

### Adding a Skill

1. Fork this repository
2. Create a new directory: `skills/<your-skill-name>/`
3. Add `skills/<your-skill-name>/SKILL.md`
4. (Optional) Add `README.md`, `references/`, `scripts/`, etc.
5. Submit a pull request

### Adding a Plugin

1. Fork this repository
2. Create a new directory: `plugins/<your-plugin-name>/`
3. Add `plugins/<your-plugin-name>/SKILL.md`
4. Add `hooks/` and/or `scripts/` directories with your executable code
5. Submit a pull request

## Agent Instructions

See [`AGENTS.md`](AGENTS.md) for the rules agents should follow when editing/adding skills and plugins.

<hr>

### Thank You to Our Contributors

<p align="center">
  <a href="https://github.com/OpenHands/extensions/graphs/contributors">
    <img src="https://assets.openhands.dev/readme/openhands-extensions-contributors.svg" />
  </a>
</p>
