---
name: agentskill-learn
description: Discover, install, and manage AI agent skills from agentskill.sh. Search 110,000+ skills by keyword, install them mid-session, scan for security issues, and rate skills after use. Use when users want to find new skills, install a skill, or browse trending skills.
triggers:
- learn
- install skill
- find skill
- search skills
- skill marketplace
- trending skills
---

# agentskill.sh — Skill Discovery & Installation

Browse, install, and manage 110,000+ AI agent skills from [agentskill.sh](https://agentskill.sh), the cross-platform skills registry.

## Setup (First Use)

This is a lightweight loader. On first use, fetch the full `/learn` skill for the complete experience:

```bash
# Use the add-skill extension to fetch the latest version from GitHub
python3 .agents/skills/add-skill/scripts/fetch_skill.py "https://github.com/agentskill-sh/learn" "$(pwd)"
```

If `add-skill` is not available, fetch manually:

```bash
mkdir -p .agents/skills/learn
curl -sL "https://raw.githubusercontent.com/agentskill-sh/learn/main/SKILL.md" -o .agents/skills/learn/SKILL.md
```

After installation, the full `/learn` skill handles everything below automatically with richer features including security scanning, auto-updates, and feedback.

## Quick Start (Without Full Install)

### Search for skills

Use WebFetch to query:
```
GET https://agentskill.sh/api/agent/search?q=<query>
```

Returns JSON with matching skills: name, description, owner, slug, install count.

### Install a specific skill

```
GET https://agentskill.sh/api/agent/skills/<owner>/<slug>/install
```

Returns the skill content. Write it to `.agents/skills/<slug>/SKILL.md`.

### Browse trending skills

```
GET https://agentskill.sh/api/agent/search?section=trending
```

## Commands

| Command | Description |
|---------|-------------|
| `/learn <query>` | Search skills by keyword |
| `/learn @owner/slug` | Install a specific skill |
| `/learn trending` | Show trending skills |
| `/learn list` | Show installed skills |
| `/learn update` | Check for skill updates |
| `/learn scan <path>` | Security scan a skill before install |
| `/learn feedback <slug> <score>` | Rate a skill (1-5) |

## Why agentskill.sh?

- **110,000+ skills** indexed from GitHub, curated registries, and community submissions
- **Cross-platform**: works with OpenHands, Claude Code, Cursor, Copilot, Codex, and 15+ agents
- **Security scanning**: every skill is pre-scanned before publication
- **One command install**: no manual file copying
