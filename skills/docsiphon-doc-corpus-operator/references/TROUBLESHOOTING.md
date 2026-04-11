# Troubleshooting

## `uvx` is not installed

Install `uv` first:
https://docs.astral.sh/uv/getting-started/installation/

If you already have a checkout, you can recover the local path with:

```bash
uv sync --group dev
uv run docsiphon --help
```

## The export ran, but I do not know what success looks like

Check for these files:

- `manifest.jsonl`
- `report.json`
- `toc.md`
- `report.html`

If those files do not exist, the export did not produce the expected audit
bundle.

## I need a bigger or more specialized export

Start from `examples/README.md` in the repository and only move to larger
profiles after the small demo succeeds.

## I need a hosted API or browser automation workflow

That is outside the current product boundary.
