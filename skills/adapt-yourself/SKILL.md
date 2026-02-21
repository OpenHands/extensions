---
name: adapt-yourself
description: Decide how to make OpenHands adapt/improve itself persistently (after restart) by choosing between repo/user skills, always-on instructions, hooks, plugins, MCP servers, or code changes in OpenHands-CLI and software-agent-sdk. Includes uv + uv tool workflows and restart/reload behavior.
triggers:
- modify yourself
- change your behavior
- customize openhands
- self-modify
- self modification
- hack openhands
- .agents/skills
- hooks.json
- plugin.json
---

# Modify OpenHands (self-modification playbook)

When a user says things like “modify yourself to do X” or “remember this next time”, **don’t jump to editing Python code**.
OpenHands has multiple extensibility layers; choose the *smallest*, *safest*, and *most persistent* mechanism that matches the user’s intent.

This skill is about **persistent** changes that should still apply after the user restarts the CLI / app.

## 0) First: clarify what kind of change the user wants

Clarify the **scope** and **type** of the change (skip questions the user already answered):

1. **Persistence scope**: Should this change apply…
   - only in *this* conversation?
   - for this *repository/workspace*?
   - for *all repos on this machine* (user-global)?
   - for *everyone* (contribution upstream / extensions registry)?
2. **Change type**: Is it primarily…
   - instructions/workflow (“when I ask for X, do Y”)?
   - a safety/policy constraint (“never run rm -rf”, “ask before network calls”)?
   - a new capability/tool integration (GitHub, Jira, internal APIs, etc.)?
   - a bug fix / UI change in the CLI or SDK?
3. **Where do they run OpenHands?**
   - `uv tool install openhands` (tool environment)
   - from a local clone (developer workflow)
   - via a remote runtime / server

Then follow the decision tree below.

## 1) Prefer non-code extensibility (often enough)

### 1.1 Write a skill (AgentSkills / progressive disclosure)

Use when the user wants repeatable expertise/workflows, e.g.:
- “When I say ‘release notes’, use this structure”
- “Here’s how we do migrations in our company”
- “We always run `make lint` before committing”

**Where to put it (in priority order):**

1. **Project-local (recommended):** `<repo>/.agents/skills/<skill-name>/SKILL.md`
2. Legacy OpenHands path: `<repo>/.openhands/skills/<skill-name>/SKILL.md`
3. **User-global:** `~/.agents/skills/<skill-name>/SKILL.md`

Notes:
- **Project skills override user + public skills** (same `name`). This is the simplest way to “patch” a public skill locally.
- Add `triggers:` only when you really want automatic activation; prefer **distinctive phrases** to avoid injecting the skill on unrelated messages.

See: [Templates](references/TEMPLATES.md#agentskillsskillmd-template).

### 1.2 Add always-on repo instructions (AGENTS.md)

Use when the user wants **always-applied** guidance for a repository (style, commands, guardrails, conventions):

- Create or edit `<repo>/AGENTS.md` (or model-specific variants like `CLAUDE.md`, `GEMINI.md` if your environment supports them).
- Put the repo rules there.

This gets loaded at conversation start as “always-on context” (not progressive disclosure).

### 1.3 Add hooks (policy/automation) via `.openhands/hooks.json`

Use when the user wants **enforcement** or **automation** around tool usage, e.g.:
- “Before any git commit, run tests.”
- “Block any command that tries to access prod without approval.”
- “Reject tool calls that write outside the repo.”

Hooks are executed on lifecycle events (like `pre_tool_use`) and can **allow / block / modify** actions.

See: [Hook templates](references/TEMPLATES.md#hookshooksjson-template) and [Hook architecture notes](references/ARCHITECTURE.md#hooks).

### 1.4 Add tools via MCP (`.mcp.json`)

Use when the user wants a **new tool** (capability) that should be available to the agent:
- internal HTTP APIs
- local services
- language servers
- DB query endpoints

MCP server configuration is **product-specific**:

- **OpenHands-CLI** persists MCP servers in `~/.openhands/mcp.json` (or `$OPENHANDS_PERSISTENCE_DIR/mcp.json`).
- **Software Agent SDK skills/plugins** use a **per-skill/per-plugin** `.mcp.json` file located inside the skill/plugin directory.

See: [MCP template](references/TEMPLATES.md#mcp-template).

### 1.5 Package it as a plugin (shareable bundle)

Use when the change should be **portable** across repos or shared with others, and it includes more than just instructions:
- skills + hooks + MCP config together
- optional slash commands and/or specialized agents

Plugins follow the Claude Code-compatible structure, with `.plugin/plugin.json` (or `.claude-plugin/plugin.json`).

See: [Plugin template](references/TEMPLATES.md#plugin-template) and [Plugin architecture notes](references/ARCHITECTURE.md#plugins).

## 2) When code changes are actually required

Choose the correct codebase / package:

- **CLI UX, TUI widgets, slash commands, config files** → `OpenHands/OpenHands-CLI`
- **Agent runtime logic, skill loading, hooks system, plugin loader, event model** → `OpenHands/software-agent-sdk` → `openhands-sdk`
- **Built-in tools (Terminal, File Editor, Task Tracker, etc.)** → `OpenHands/software-agent-sdk` → `openhands-tools`
- **Workspace mounting / file sync / workspace abstraction** → `OpenHands/software-agent-sdk` → `openhands-workspace`

If you’re not sure, start by reproducing the issue and locating the code path.

## 3) uv development workflows (including `uv tool install openhands`)

Keep this section **high-level**; the goal is to pick the right workflow, not memorize `uv`.

- If they run OpenHands from a **local clone**: use `uv sync` + `uv run openhands`.
- If they installed OpenHands via **`uv tool install openhands`**:
  - safest: `uv tool run --from /path/to/OpenHands-CLI openhands`
  - persistent: `uv tool install --force --editable /path/to/OpenHands-CLI`
- If they need to modify the **SDK** while running the CLI, remember: the CLI often **pins exact SDK/tool versions**. Prefer aligning versions; use overrides only for local development.

Details: [Installation modes (`uv tool` vs `uv run`)](references/INSTALLATION_MODES.md).

## 4) What requires a restart to take effect?

- **Skills / AGENTS.md**: typically loaded at conversation start → restart the app/CLI (or start a new conversation) to guarantee reload.
- **Hooks (.openhands/hooks.json)**: loaded when the agent/conversation initializes → restart to guarantee reload.
- **Plugins**: loaded when the conversation initializes → restart to guarantee reload.
- **Editable Python code (uv tool `--editable` or local `uv run`)**: changes apply the next time the Python process starts.

## 5) Verification checklist

After making a “self-modification” change:

1. Restart OpenHands.
2. In the CLI, run `/skills` to confirm the expected skills/hooks/MCPs are loaded.
3. Trigger the workflow with a tiny, deterministic test prompt.
4. If it’s a code change, run the smallest relevant test suite (or add one).

## References

- [Architecture: CLI vs SDK vs skills/hooks/plugins](references/ARCHITECTURE.md)
- [Installation modes: `uv tool` vs `uv run` and version pinning](references/INSTALLATION_MODES.md)
- [Templates: SKILL.md, hooks.json, plugin.json, .mcp.json](references/TEMPLATES.md)
