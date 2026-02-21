# Installation and development modes (uv)

This reference is for making “persistent self-modifications” that apply after restart.

## `uv run` (project environment) mode

Use when you are developing from a git clone.

- `uv sync` installs dependencies into a project-local `.venv/` (and/or uses the uv lockfile).
- `uv run ...` runs inside that environment.

Typical CLI dev flow:

```bash
cd OpenHands-CLI
uv sync --group dev
uv run openhands
```

Typical SDK dev flow:

```bash
cd software-agent-sdk
uv sync --group dev
uv run pytest
```

### Pros

- Simple debugging (local sources)
- Easy to run tests + linters
- No global tool replacement needed

### Cons

- You must run `openhands` via `uv run openhands` (or ensure the venv is on PATH)

## `uv tool install openhands` (tool environment) mode

In this mode, `uv` installs the CLI into a dedicated tool environment and exposes a shim executable.

### Inspect installed tools

```bash
uv tool list
uv tool dir
```

If `openhands` is installed and not found on PATH, run:

```bash
uv tool update-shell
```

### Replace the tool with an editable local checkout

This is the most common way to run a modified CLI *after restart*:

```bash
uv tool install --force --editable /path/to/OpenHands-CLI
```

After that, `openhands` should use the editable sources.

### Run a local checkout without installing

This is the safest way to test a change:

```bash
uv tool run --from /path/to/OpenHands-CLI openhands
```

## SDK vs CLI version pins

The CLI often pins exact versions of:

- `openhands-sdk`
- `openhands-tools`
- `openhands-workspace`

If you want to use a local SDK checkout *together with the CLI*, you must handle that pinning.

### What usually works

1. Check the versions the CLI requires:
   - `OpenHands-CLI/pyproject.toml`
2. Check out the matching tag/commit in `software-agent-sdk`.
3. Install the matching SDK packages in editable mode into the environment that runs the CLI.

### What commonly fails

Trying to install an SDK checkout at version `X` into an environment where the CLI requires `openhands-sdk==Y`.

### Using `--overrides` for development

As a last resort for local development, you can override pinned deps.

Create a file (e.g. `overrides.txt`) containing a direct URL or local path spec:

```text
openhands-sdk @ file:///absolute/path/to/software-agent-sdk/openhands-sdk
openhands-tools @ file:///absolute/path/to/software-agent-sdk/openhands-tools
openhands-workspace @ file:///absolute/path/to/software-agent-sdk/openhands-workspace
```

Then install the CLI tool using that overrides file:

```bash
uv tool install --force --editable /path/to/OpenHands-CLI --overrides overrides.txt
```

Notes:
- This is intentionally “break glass”; it can produce a mismatched runtime.
- Prefer aligning versions whenever possible.
