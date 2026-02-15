# add-skill

Add (import) an OpenHands skill from a GitHub repository into the current workspace.

This skill is useful when a user says things like:

- “Add the `codereview` skill from https://github.com/OpenHands/extensions/”
- “/add-skill https://github.com/OpenHands/extensions/tree/main/skills/codereview”

It fetches only the requested skill directory (via git sparse checkout) and installs it into the workspace so OpenHands can use it.

## What it does

- Parses a GitHub URL (multiple formats supported)
- Downloads only the requested skill folder (no full repo clone)
- Validates the downloaded folder contains a `SKILL.md`
- Installs the skill into:

```text
<workspace>/.agents/skills/<skill-name>/
```

## Included files

- `SKILL.md` – skill metadata + usage guidance for the agent
- `scripts/fetch_skill.py` – implementation used to fetch/install a skill

## Usage

From the `add-skill` skill directory:

```bash
python3 scripts/fetch_skill.py "<github-skill-url>" "<workspace-path>" [--force]
```

### Examples

```bash
# Full URL with explicit branch
python3 scripts/fetch_skill.py \
  "https://github.com/OpenHands/extensions/tree/main/skills/docker" \
  "/workspace"

# Shorthand form (defaults to main)
python3 scripts/fetch_skill.py \
  "OpenHands/extensions/skills/codereview" \
  "/workspace"

# Overwrite if the skill already exists
python3 scripts/fetch_skill.py \
  "OpenHands/extensions/tree/main/skills/codereview" \
  "/workspace" \
  --force
```

## Supported URL formats

- `https://github.com/<owner>/<repo>/tree/<branch>/<path/to/skill>`
- `https://github.com/<owner>/<repo>/<path/to/skill>` (defaults to `main`)
- `github.com/<owner>/<repo>/<path/to/skill>`
- `<owner>/<repo>/<path/to/skill>`

## Notes / caveats

- If `GITHUB_TOKEN` is set, it will be used for authentication (needed for private repos).
- If the destination already exists, the script will fail unless `--force` is provided.
- The script installs under `.agents/skills/`.
