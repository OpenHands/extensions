# OpenHands Extensions — Agent Notes

This repository (`OpenHands/extensions`) is the **public extensions registry** for OpenHands.
It contains **shareable skills and plugins** that can be loaded by OpenHands (CLI/GUI/Cloud) and by client code using the **Software Agent SDK**.

## What this repo contains

- `skills/` — a catalog of skills, **one directory per skill**.
  - `skills/<skill-name>/SKILL.md` — the skill definition (AgentSkills-style progressive disclosure)
  - `skills/<skill-name>/README.md` — optional extra docs/examples for humans

- `plugins/` — a catalog of plugins with executable code components.
  - `plugins/<plugin-name>/SKILL.md` — the plugin definition
  - `plugins/<plugin-name>/hooks/` — lifecycle hooks (optional)
  - `plugins/<plugin-name>/scripts/` — utility scripts (optional)

There is no application code here; the primary artifacts are Markdown skill definitions and plugin configurations, which can contain `scripts/`, `hooks/` sub-directories.

## How client code uses this repo

### OpenHands Applications

OpenHands can load skills from a project directory (repo-level) and from user-level locations.
This repository is the **global/public** registry referenced by the docs.

### Skill loading models to know

OpenHands supports two complementary mechanisms:

1. **Always-on context (repository rules)**
   - Loaded at conversation start.
   - Prefer a root `AGENTS.md` (and optionally model-specific variants like `CLAUDE.md` / `GEMINI.md`).

2. **AgentSkills (progressive disclosure), with an OpenHands extension for keyword triggers**
   - Each skill lives in its own directory with a `SKILL.md` entry point.
   - The agent is shown a catalog (name/description/location) and decides when to open/read the full content.
   - **OpenHands extension**: the `SKILL.md` may include optional `triggers:` frontmatter to enable keyword-based activation.

This registry primarily provides (2). Client repositories typically add (1) for repo-specific, always-on instructions.

### Software Agent SDK

SDK consumers typically load skills either:

- as **always-loaded context** (e.g., `AGENTS.md`), and/or
- as **trigger-loaded keyword skills**, and/or
- as **progressive-disclosure AgentSkills** by discovering `SKILL.md` files under a directory.

See: https://docs.openhands.dev/sdk/guides/skill

## AgentSkills / Skill authoring rules (follow these)

OpenHands uses an **extended AgentSkills standard**:

- **Compatible with the AgentSkills specification** (https://agentskills.io/specification)
- **Extended with optional `triggers:` frontmatter** for keyword-based activation

When editing or adding skills in this repo, follow these rules (and add new skills to `marketplaces/openhands-extensions.json`):

1. **One skill per directory**
   - Create `skills/<skill-name>/SKILL.md`.
   - Keep the directory name stable; it is used as the skill identifier/location.

2. **SKILL.md should be progressive disclosure**
   - Put a concise summary/description first.
   - Include only the information needed for an agent to decide whether to open/read the skill.
   - If the skill needs large references, keep them in the same directory (e.g., `references/`) and point to them.

3. **Be specific and operational**
   - Prefer checklists, steps, and concrete examples.
   - Avoid vague guidance like “be careful” without actionable criteria.

4. **Avoid repo-local assumptions**
   - Skills here are **public and reusable**.
   - Don’t reference private paths, secrets, or company-specific URLs.

5. **Do not include secrets or sensitive data**
   - Never commit API keys, tokens, credentials, private endpoints, or internal customer data.

6. **Prefer minimal, composable skills**
   - Keep a skill focused on a single domain/task.
   - If it grows large, split it into multiple skills.

7. **Compatibility notes**
   - The legacy `.openhands/microagents/` location may still exist in user repos, but this registry uses the current skills layout.

## Repository conventions

- **Punctuation style**: Use plain hyphens (`-`) instead of em dashes (`—` / `\u2014`) in skill descriptions, SKILL.md content, and marketplace JSON entries.
- Keep formatting consistent across skills.
- If you change a skill’s behavior or scope, update its `README.md` (if present) accordingly.
- If you change top-level documentation, ensure links still resolve.
- For Python test runs, prefer `uv sync --group test` followed by `uv run pytest -q`; the full suite depends on `openhands-sdk`, which is not available in the base environment.
- Agent-driven plugins (for example `plugins/pr-review` and `plugins/release-notes`) use `uv run --with openhands-sdk --with openhands-tools ...` and require an `LLM_API_KEY` in addition to `GITHUB_TOKEN`.
- For OpenHands Cloud API guidance, automations, and CLI integration, use `plugins/openhands`. It is the canonical unified OpenHands plugin covering the V1 Cloud API, Automations API, and CLI. The individual skills (`skills/openhands-api`, `skills/openhands-automation`) are also available standalone.
- When reviewing or editing `skills/openhands-sdk`, validate copy-paste imports against the released packages with `uv run --with openhands-tools --with openhands-workspace --with openhands-agent-server python ...`. In the current released workspace package, the exported remote workspace classes are `APIRemoteWorkspace` / `OpenHandsCloudWorkspace`; `RemoteAPIWorkspace` is not available.
- For agent-driven plugin scripts, prefer `from openhands.sdk.plugin import PluginSource` and pass `plugins=[PluginSource(source=...)]` into `Conversation`. In the current released SDK (`openhands-sdk` 1.18.x), `Plugin` is not exported from `openhands.sdk.plugin`, so direct `Plugin.load(...)` imports can break CI.
- `plugins/qa-changes/action.yml` now has a preflight guard for fork PRs in `pull_request` context: if the PR comes from a fork and `LLM_API_KEY` is unavailable (normal for forks), the action exits successfully with a clear skip notice instead of failing.

- `plugins/release-notes` now has a standalone validator at `plugins/release-notes/scripts/validate_release_notes.py`; it rebuilds the deterministic tag-range context, fails if a change bullet omits explicit PR/commit refs or matching author handles, and enforces full PR/author coverage by appending a compact `### 🔎 Small Fixes/Internal Changes` appendix grouped by author when the agent omits lower-signal items. New contributor detection in `generate_release_notes.py` should use merged PR history for human authors (excluding bots) rather than commit-author lookup.


## CI / validation gotchas

- The test suite expects **every directory under `skills/`** to be listed in a marketplace. If you add a new skill (or rebase onto a main branch that added skills), update the appropriate marketplace file or CI will fail with `Skills missing from marketplace: [...]`.
- `scripts/sync_extensions.py` keeps generated artifacts in sync: Claude Code command files, README catalog section, coverage checks, and vendor symlinks. Run `python scripts/sync_extensions.py --check` (or just push — CI runs it) to verify everything is consistent. Run without `--check` to auto-fix. The "Quick Start" section in `README.md` (OpenHands SDK, Claude Code, and Codex setup instructions) is **manually maintained** above the auto-generated catalog markers and is intentionally not generated by the sync script.
- The sync script uses PyYAML to parse SKILL.md frontmatter. If you add a skill with a slash trigger (e.g., `triggers: ["/mycommand"]`), the script auto-generates `commands/mycommand.md`. **Note:** Slash triggers in SKILL.md frontmatter are deprecated — prefer adding a `commands/command-name.md` file to the plugin's `commands/` directory instead. Keyword triggers (non-slash) remain the recommended way to activate skills by topic.

## OpenHands SDK documentation policy

- **Do NOT add SDK-specific or SDK-related documentation to this repo.** The canonical source of truth for SDK documentation is the [OpenHands docs site](https://docs.openhands.dev/sdk) and its structured index at <https://docs.openhands.dev/llms.txt>.
- The `skills/openhands-sdk/SKILL.md` is **auto-generated** by `scripts/sync_openhands_sdk_skill.py`. It pulls class names, guides, examples, and the hello-world snippet directly from the docs site and the SDK repo. **Do not edit SKILL.md by hand** - run the script to regenerate it.
- CI runs `python scripts/sync_openhands_sdk_skill.py --check` on every PR. If the skill is out of date, regenerate it with `python scripts/sync_openhands_sdk_skill.py`.
- If a PR adds or modifies SDK-specific documentation in this repo, **push back**: ask the submitter to contribute those changes to [OpenHands/docs](https://github.com/OpenHands/docs) instead.

## PR review plugin notes

- The `code-review` and `codereview-roasted` skills have been merged into a single `code-review` skill. The `/codereview-roasted` trigger is kept as an alias for backward compatibility. The `review-style` action input is deprecated and ignored.
- `plugins/pr-review` supports an optional `require-evidence` action input that tells the reviewer to require end-to-end proof in the PR description that the code works; test output alone is not sufficient evidence.
- The corresponding `REQUIRE_EVIDENCE` env flag is consumed by `plugins/pr-review/scripts/agent_script.py` and injected into the review prompt via `plugins/pr-review/scripts/prompt.py`.
- `plugins/pr-review` exposes an `enable-uv-cache` input (default `'false'`) that toggles `setup-uv`'s GitHub Actions cache. Default stays off because a prompt-injected reviewer could poison a shared cache that higher-privilege workflows later consume; opt in only on single-tenant self-hosted runners. The README's "Caching and Security" section documents the threat model and recommends a host-level uv cache volume as the preferred alternative for self-hosted setups.
- GitHub review suggestions that only delete lines can look empty in `PullRequestReviewComment.body`; the rendered content is available via `bodyText`/`bodyHTML`, so review-context formatting should fall back there before treating a suggestion as empty.
- Prompt coverage for this behavior lives in `tests/test_pr_review_prompt.py`.

## When uncertain

- Prefer the official OpenHands docs on skills: https://docs.openhands.dev/overview/skills
- Prefer the SDK skill guide: https://docs.openhands.dev/sdk/guides/skill
