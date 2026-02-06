---
name: add-skill
description: Add an external skill from a GitHub repository to the current workspace. Use when users want to import, install, or add a skill from a GitHub URL (e.g., `/add-skill https://github.com/owner/repo/skill-name` or "add the vercel skill from github.com/rbren/agent-skills"). Handles fetching the skill files and placing them in .openhands/skills/.
---

# Add Skill

Import skills from GitHub repositories into the current workspace.

## Workflow

When a user requests to add a skill from a GitHub URL:

1. **Parse the URL** to extract repository owner, name, and skill path
2. **Fetch the skill** using the bundled script:
   ```bash
   python3 <this-skill-path>/scripts/fetch_skill.py "<github-url>" "<workspace-path>"
   ```
3. **Verify** that SKILL.md exists in the destination
4. **Inform the user** the skill is now available

## URL Formats Supported

- `https://github.com/owner/repo/tree/main/path/to/skill`
- `https://github.com/owner/repo/skill-name`
- `github.com/owner/repo/skill-name`
- `owner/repo/skill-name` (shorthand)

## Example

User: `/add-skill https://github.com/rbren/agent-skills/vercel-skill`

```bash
# Run the fetch script
python3 scripts/fetch_skill.py "https://github.com/rbren/agent-skills/vercel-skill" "/path/to/workspace"

# Verify installation
ls /path/to/workspace/.openhands/skills/vercel-skill/SKILL.md
```

Response: "✅ Added `vercel-skill` to your workspace. The skill is now available."

## Notes

- Creates `.openhands/skills/` directory if it doesn't exist
- Uses `GITHUB_TOKEN` for authentication (required for private repos)
- Warns before overwriting existing skills with the same name
