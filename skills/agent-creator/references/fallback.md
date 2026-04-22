# Fallback Spec — OpenHands File-Based Agent

> Use this file ONLY if fetching https://docs.openhands.dev/sdk/guides/agent-file-based fails.
> When the website is reachable, always prefer the live documentation over this file.

## Agent File Format

A file-based sub-agent is a single `.md` file with YAML frontmatter and a Markdown body.
The frontmatter configures the agent. The Markdown body becomes the agent's system prompt.

## Frontmatter Fields

| Field | Required | Default | Description |
|---|---|---|---|
| `name` | Yes | — | agent identifier,lowercase + hyphens, matches filename exactly |
| `description` | No | `""` | What this agent does. Shown to orchestrator. Add `<example>` tags |
| `tools` | No | `[]` | List of tools the agent can use (for example: `file_editor`, `terminal`, `browser_tool_set`, etc)|
| `model` | No | `inherit` | LLM model profile to load and use for the subagent ("inherit" uses the parent agent’s model) |
| `skills` | No | `[]` | List of skill names for this agent |
| `max_iteration_per_run` | No | `None` | 	Maximum iterations per run. Must be strictly positive, or `None` for the default value.|
| `color` | No | `None` | Rich color name (e.g., "blue", "green") used by visualizers to style this agent’s output in terminal panels |
| `mcp_servers` | No | `None` | MCP server configs |
| `hooks` | No | `None` | Hook configuration for lifecycle events |
| `permission_mode` | No | `None` | `always_confirm` / `never_confirm` / `confirm_risky` |
| `profile_store_dir` | No | `None` | Custom directory path for LLM profiles when using a named model|

## Directory Conventions

Place agent files in these directories, scanned in priority order (first match wins):

| Priority | Path | Scope |
|---|---|---|
| 1 | `{project}/.agents/agents/<name>.md` | Project (primary) |
| 2 | `{project}/.openhands/agents/<name>.md` | Project (secondary) |
| 3 | `~/.agents/agents/<name>.md` | User (primary) |
| 4 | `~/.openhands/agents/<name>.md` | User (secondary) |

**Rules:**
- Filename = agent name exactly (`name: code-reviewer` → `code-reviewer.md`)
- Place file directly in `agents/` — do NOT create subdirectories
- `README.md` is automatically skipped by the loader
- Project-level takes priority over user-level when names conflict

## \<example> Tags

Add \<example> tags inside the description to help the orchestrating agent know when to delegate to this agent:

For example
```markdown
description: >
  Writes and improves technical documentation.
  <example>Write docs for this module</example>
  <example>Improve the README</example>
```

## Minimal Valid Example

```markdown
---
name: code-reviewer
description: >
  Reviews code for quality, bugs, and best practices.
  <example>Review this pull request for issues</example>
  <example>Check this code for bugs</example>
tools:
  - file_editor
  - terminal
model: inherit
---

# Code Reviewer

You are a meticulous code reviewer. When reviewing code:

1. **Correctness** - Look for bugs, off-by-one errors, and race conditions.
2. **Style** - Check for consistent naming and idiomatic usage.
3. **Performance** - Identify unnecessary allocations or algorithmic issues.
4. **Security** - Flag injection vulnerabilities or hardcoded secrets.

Keep feedback concise and actionable. For each issue, suggest a fix.
```

## Generated File Template

~~~markdown
---
name: <agent-name>
description: >
  <One imperative sentence — what this agent does and when to use it.>
  <example>A concrete user request this agent handles</example>
  <example>Another concrete delegation trigger</example>
tools:
  - <tool-name>
model: inherit
permission_mode: <always_confirm|never_confirm|confirm_risky>
---

# <Title>

<One paragraph: role, approach, and primary constraint. Written in second person — "You are...">

## How to Execute

<Numbered steps — what the AGENT thinks and does, not what the user provides.>

## Output Format

<Concrete Markdown template — not a prose description.>

## Gotchas

- Do not <most likely wrong behavior specific to this domain>.

## Edge Cases

- **<Specific case>**: <Exact handling — not generic advice>.
~~~
