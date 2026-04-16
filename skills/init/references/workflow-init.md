# Quick Init — `/init`

Scaffold a concise, repo-specific `AGENTS.md`.

## Target path rules

- `/init`: create `AGENTS.md` at the repository root.
- `/init <path>`: create `AGENTS.md` scoped to `<path>`.
  - If `<path>` is a directory, write `<path>/AGENTS.md`.
  - If `<path>` ends with `.md`, treat it as the full output file path.

Never overwrite an existing file silently. If the target file already exists,
ask the user whether to (a) keep it, (b) edit it, or (c) replace it.

## Workflow

1. **Inspect the repo to tailor the guide**
   - Skim top-level structure (`ls`, `find -maxdepth 2`).
   - Read the primary docs (`README*`, `CONTRIBUTING*`, `DEVELOPMENT*`, `Makefile`).
   - Identify build tooling and common commands (`pyproject.toml`, `package.json`, CI configs).
   - Locate tests and how they are run (`tests/`, workflow YAMLs, task runners).

2. **Write a concise `AGENTS.md`** using the spec below.

3. **Create the file** at the target location.

## `AGENTS.md` spec

- Title the document: `# Repository Guidelines`.
- Use Markdown headings (`##`) to organize sections.
- Keep it concise: **200–400 words**.
- Keep explanations short, direct, and specific to the repo.
- Prefer concrete examples (commands, directory paths, naming patterns).

### Recommended sections (adapt as needed)

- Project Structure & Module Organization
- Build, Test, and Development Commands
- Coding Style & Naming Conventions
- Testing Guidelines
- Commit & Pull Request Guidelines
- Optional: Security & Configuration Tips, Architecture Overview, Agent-specific instructions

## Content guidelines

- Only include information that's broadly useful for future tasks (avoid one-off issue details).
- If the repo already contains nested `AGENTS.md` files, briefly mention that more deeply nested files override broader ones within their directory tree.
