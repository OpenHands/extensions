# `/init` skill

This skill helps an agent generate an `AGENTS.md` file (a concise contributor/repo-guidelines doc for AI-assisted development).

## Usage

- `/init` → create `AGENTS.md` at the repository root.
- `/init <path>` → create `AGENTS.md` scoped to the given path:
  - If `<path>` is a directory, the file is written to `<path>/AGENTS.md`.
  - If `<path>` ends with `.md`, it is treated as the output file path.

The generated document follows a short, repo-specific template (structure, commands, style, testing, PR conventions) and avoids overwriting any existing `AGENTS.md` without confirmation.
