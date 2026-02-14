# OpenHands Skills Registry — Agent Notes

This repository (`OpenHands/skills`) is the **public skills registry** for OpenHands.
It contains **shareable skills** that can be loaded by OpenHands (CLI/GUI/Cloud) and by client code using the **Software Agent SDK**.

## What this repo contains

- `skills/` — a catalog of skills, **one directory per skill**.
  - `skills/<skill-name>/SKILL.md` — the skill definition (AgentSkills-style progressive disclosure)
  - `skills/<skill-name>/README.md` — optional extra docs/examples for humans

There is no application code here; the primary artifacts are Markdown skill definitions, though they can contain `scripts/`, `hooks/` sub-directories as part of the Agentskill.

## How client code uses this repo

### Apps based on OpenHands SDK

OpenHands can load skills from a project directory (repo-level) and from user-level locations.
This repository is the **global/public** registry referenced by the docs.

### Skill loading models to know (always-on vs triggered)

OpenHands supports multiple ways to load instructions:

1. **Always-on context**
   - Loaded at conversation start (repo-wide rules).
   - Prefer a root `AGENTS.md` (and optionally `CLAUDE.md` / `GEMINI.md`) in a repository.

2. **Trigger-based (keyword) skills**
   - Loaded only when matching keywords appear in user messages.
   - Often used for narrow domain expertise (e.g., Docker, Kubernetes).

3. **Progressive disclosure (AgentSkills standard)**
   - The agent is shown a catalog (name/description/location) and decides when to open/read full content.
   - Implemented as one directory per skill with a `SKILL.md` entry point.

This registry primarily provides (3), but OpenHands commonly pairs it with (1) and (2) in client repos.

### Software Agent SDK

SDK consumers typically load skills either:

- as **always-loaded context** (e.g., `AGENTS.md`), and/or
- as **trigger-loaded keyword skills**, and/or
- as **progressive-disclosure AgentSkills** by discovering `SKILL.md` files under a directory.

See: https://docs.openhands.dev/sdk/guides/skill

## AgentSkills / Skill authoring rules (follow these)

OpenHands supports an extended version of the **AgentSkills** standard (https://agentskills.io/specification).
When editing or adding skills in this repo, follow these rules:

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

- Keep formatting consistent across skills.
- If you change a skill’s behavior or scope, update its `README.md` (if present) accordingly.
- If you change top-level documentation, ensure links still resolve.

## When uncertain

- Prefer the official OpenHands docs on skills: https://docs.openhands.dev/overview/skills
- Prefer the SDK skill guide: https://docs.openhands.dev/sdk/guides/skill
