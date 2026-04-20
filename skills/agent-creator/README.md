# agent-creator

A skill for OpenHands that creates file-based sub-agents through a structured interview workflow. Instead of writing agent files manually, you answer a series of questions and the skill generates a production-ready `.md` file following the official OpenHands SDK specification.

## What It Does

- Guides you through a requirements interview (goal, input, output, tools, permissions, etc.)
- Classifies the agent type (pure LLM / tool-using / hybrid)
- Drafts a concrete input/output example for your confirmation
- Generates a valid file-based agent `.md` file
- Saves it to the correct project-level or user-level path

## Usage

Trigger with the `/agent-creator` command, or just describe what you want:

```
/agent-creator
```

```
I want to create an agent that reviews pull requests
```

## Generated File Format

The skill produces a single `.md` file following the [OpenHands file-based agent spec](https://docs.openhands.dev/sdk/guides/agent-file-based):

```markdown
---
name: my-agent
description: >
  What this agent does.
  <example>A concrete delegation trigger</example>
tools:
  - file_editor
  - terminal
model: inherit
permission_mode: always_confirm
---

# My Agent

You are a specialized agent that...

## How to Execute
...

## Output Format
...

## Gotchas
...

## Edge Cases
...
```

## Where Files Are Saved

| Scope | Primary path |
|---|---|
| Project-level | `{project}/.agents/agents/<name>.md` |
| User-level | `~/.agents/agents/<name>.md` |

> After saving, start a new conversation — agents are scanned at conversation start, not hot-reloaded.

## File Structure

```
agent-creator/
├── SKILL.md              # Skill definition and interview workflow
└── references/
    └── fallback.md       # OpenHands agent spec (used if live docs are unreachable)
```

The skill always tries to fetch the latest spec from the official OpenHands docs first. If the fetch fails, it falls back to `references/fallback.md`.

## Interview Questions

The skill asks these questions one at a time:

1. Goal and scope
2. Input format and source
3. Output format and structure
4. Constraints and non-goals
5. Success criteria
6. Edge cases
7. Gotchas
8. Tools needed
9. Permission mode
10. Project-level or user-level scope

## Requirements

- OpenHands with a configured LLM
- No additional dependencies for pure LLM agents
- `file_editor` and/or `terminal` tools available for tool-using agents

## Related Docs

- [File-Based Agents](https://docs.openhands.dev/sdk/guides/agent-file-based)
- [Agent Skills & Context](https://docs.openhands.dev/sdk/guides/skill)
- [OpenHands Extensions Registry](https://github.com/OpenHands/extensions)
