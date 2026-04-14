# OpenHands Extensions

This repository is the **public extensions registry** for [OpenHands](https://github.com/OpenHands/OpenHands).
It contains reusable, shareable skills and plugins that customize agent behavior.

- Skills overview docs: https://docs.openhands.dev/overview/skills
- SDK skill guide: https://docs.openhands.dev/sdk/guides/skill

## Installation

### OpenHands (automatic)

All extensions in this registry are **automatically available** to OpenHands agents (Cloud, CLI, and GUI). No manual installation is needed — OpenHands loads these skills at runtime.

### Claude Code

You can install this registry as a [Claude Code plugin marketplace](https://docs.anthropic.com/en/docs/claude-code/plugins):

```bash
claude plugins add-marketplace https://github.com/OpenHands/extensions
```

This registers the **OpenHands Extensions** marketplace. You can then discover and install individual skills:

```bash
claude plugins discover
claude plugins install <skill-name>
```

To install a single skill without the full marketplace, point Claude Code at the specific plugin directory:

```bash
claude plugins install https://github.com/OpenHands/extensions/tree/main/skills/<skill-name>
```

### Other Coding Agents

Extensions follow the [AgentSkills specification](https://agentskills.io/specification). Each skill is a directory with a `SKILL.md` entry point that any compatible agent can consume.

**Manual import** — copy a skill directory into your project:

```bash
# Clone just the skill you need (using git sparse-checkout)
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/OpenHands/extensions.git
cd extensions
git sparse-checkout set skills/<skill-name>
cp -r skills/<skill-name> /path/to/your/project/.agents/skills/
```

**AGENTS.md reference** — alternatively, point your agent at the skill content by
referencing it in your project's `AGENTS.md`:

```markdown
See: https://github.com/OpenHands/extensions/blob/main/skills/<skill-name>/SKILL.md
```

## Catalog

<!-- BEGIN AUTO-GENERATED CATALOG -->
This repository contains **2 marketplace(s)** with **38 skills** and **9 plugins**.

### large-codebase

OpenHands skills for interacting, improving, and refactoring large codebases

**2 skills, 2 plugins**

```bash
claude plugins add-marketplace https://github.com/OpenHands/extensions  # registers "large-codebase"
```

| Name | Type | Description | Commands |
|------|------|-------------|----------|
| add-javadoc | skill | Add comprehensive JavaDoc documentation to Java classes and methods. Use when documenting Java code, adding API docum... | — |
| cobol-modernization | plugin | End-to-end COBOL to Java migration workflow. Handles build setup, mainframe dependency removal, and code migration wi... | — |
| migration-scoring | plugin | Evaluate code migration quality with coverage, correctness, and style scoring. Generates executive reports with actio... | — |
| spark-version-upgrade | skill | Upgrade Apache Spark applications between major versions (2.x→3.x, 3.x→4.x). Covers build files, deprecated APIs, con... | — |

### openhands-extensions

Official OpenHands extensions marketplace - reusable skills and plugins that customize agent behavior

**36 skills, 7 plugins**

```bash
claude plugins add-marketplace https://github.com/OpenHands/extensions  # registers "openhands-extensions"
```

| Name | Type | Description | Commands |
|------|------|-------------|----------|
| add-skill | skill | Add (import) an OpenHands skill from a GitHub repository into the current workspace. | — |
| agent-memory | skill | Persist and retrieve repository-specific knowledge using AGENTS.md files. Use when you want to save important informa... | `/remember` |
| agent-sdk-builder | skill | Guided workflow for building custom AI agents using the OpenHands Software Agent SDK. Use when you want to create a n... | `/agent-builder` |
| automation | skill | Create and manage OpenHands automations - scheduled tasks that run in sandboxes. Use the prompt preset to create auto... | — |
| automation-creation | plugin | Interactive slash command for creating OpenHands automations from a natural language prompt. Provides /automation:cre... | — |
| azure-devops | skill | Interact with Azure DevOps repositories, pull requests, and APIs using the AZURE_DEVOPS_TOKEN environment variable. U... | — |
| babysit-pr | skill | Babysit a GitHub pull request by monitoring CI checks, workflow runs, review comments, and mergeability until it is r... | `/babysit-pr`, `/babysit` |
| bitbucket | skill | Interact with Bitbucket repositories and pull requests using the BITBUCKET_TOKEN environment variable. Use when worki... | — |
| city-weather | plugin | Get current weather, time, and precipitation forecast for any city using the free Open-Meteo API. Provides slash comm... | — |
| code-review | skill | Structured code review covering style, readability, and security concerns with actionable feedback. Use when reviewin... | `/codereview` |
| codereview-roasted | skill | Brutally honest code review in the style of Linus Torvalds, focusing on data structures, simplicity, and pragmatism. ... | `/codereview-roasted` |
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
| jupyter | skill | Read, modify, execute, and convert Jupyter notebooks programmatically. Use when working with .ipynb files for data sc... | — |
| kubernetes | skill | Set up and manage local Kubernetes clusters using KIND (Kubernetes IN Docker). Use when testing Kubernetes applicatio... | — |
| learn-from-code-review | skill | Distill code review feedback from GitHub PRs into reusable skills and guidelines. Use when users ask to learn from co... | `/learn-from-reviews` |
| linear | skill | Interact with Linear project management - query issues, update status, create tickets using the Linear GraphQL API. | — |
| magic-test | plugin | A simple test plugin for verifying plugin loading. Triggers on magic words (alakazam, abracadabra) and returns a spec... | — |
| notion | skill | Create, search, and update Notion pages/databases using the Notion API. Use for documenting work, generating runbooks... | — |
| npm | skill | Handle npm package installation in non-interactive environments by piping confirmations. Use when installing Node.js ... | — |
| onboarding | plugin | Assess repository agent-readiness across five pillars, propose high-impact fixes, and generate repo-specific AGENTS.m... | — |
| onboarding-agent | skill | Interactive onboarding workflow that interviews users to understand their coding goals and generates PR-ready impleme... | `/onboard` |
| openhands-api | skill | Use the OpenHands Cloud REST API (V1) to create and manage app conversations, including multi-conversation delegation... | — |
| pdflatex | skill | Install and use pdflatex to compile LaTeX documents into PDFs on Linux. Use when generating academic papers, research... | — |
| pr-review | plugin | Automated PR code review — analyzes diffs and posts inline review comments via the GitHub API. | — |
| release-notes | plugin | Generate consistent, well-structured release notes from git history. Produces categorized changelog with breaking cha... | `/release-notes`, `/releasenotes` |
| releasenotes | skill | Generate formatted changelogs from git history since the last release tag. Use when preparing release notes that cate... | `/releasenotes` |
| security | skill | Security best practices for secure coding, authentication, authorization, and data protection. Use when developing fe... | — |
| skill-creator | skill | Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an ex... | — |
| ssh | skill | Establish and manage SSH connections to remote machines, including key generation, configuration, and file transfers.... | — |
| swift-linux | skill | Install and configure Swift programming language on Debian Linux for server-side development. Use when building Swift... | — |
| theme-factory | skill | Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reportings, HTML landing pages, etc.... | — |
| uv | skill | Common project, dependency, and environment operations using uv. | — |
| vercel | skill | Deploy and manage applications on Vercel, including preview deployments and deployment protection. | — |
| vulnerability-remediation | plugin | Automated security vulnerability scanning and AI-powered remediation. Scans repositories, skips when no issues found,... | — |
<!-- END AUTO-GENERATED CATALOG -->

## Repository Layout

**Skills** (`skills/`) — Markdown-based guidelines providing domain-specific knowledge:
- `skills/<skill-name>/SKILL.md` — the skill definition
- `skills/<skill-name>/commands/` — Claude Code slash commands (auto-generated from triggers)

**Plugins** (`plugins/`) — Extensions with executable code components:
- `plugins/<plugin-name>/SKILL.md` — the plugin definition
- `plugins/<plugin-name>/hooks/` — lifecycle hooks
- `plugins/<plugin-name>/scripts/` — utility scripts

**Marketplaces** (`marketplaces/`) — Curated collections of extensions (JSON manifests).

## Contributing

### Adding a Skill

1. Fork this repository
2. Create a new directory: `skills/<your-skill-name>/`
3. Add `skills/<your-skill-name>/SKILL.md`
4. Add an entry to `marketplaces/openhands-extensions.json` (or the appropriate marketplace)
5. Run `python scripts/sync_extensions.py` to generate command files and update the catalog
6. (Optional) Add `README.md`, `references/`, `scripts/`, etc.
7. Submit a pull request

### Adding a Plugin

1. Fork this repository
2. Create a new directory: `plugins/<your-plugin-name>/`
3. Add `plugins/<your-plugin-name>/SKILL.md`
4. Add `hooks/` and/or `scripts/` directories with your executable code
5. Add an entry to `marketplaces/openhands-extensions.json` (or the appropriate marketplace)
6. Run `python scripts/sync_extensions.py` to generate command files and update the catalog
7. Submit a pull request

## Agent Instructions

See [`AGENTS.md`](AGENTS.md) for the rules agents should follow when editing/adding skills and plugins.

<hr>

### Thank You to Our Contributors

<p align="center">
  <a href="https://github.com/OpenHands/extensions/graphs/contributors">
    <img src="https://assets.openhands.dev/readme/openhands-extensions-contributors.svg" />
  </a>
</p>
