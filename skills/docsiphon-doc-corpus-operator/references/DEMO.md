# Demo

Use this exact first-success path before trying bigger targets:

```bash
uvx --from git+https://github.com/xiaojiou176-open/docsiphon.git \
  docsiphon "https://developerdocs.instructure.com/services/canvas" \
  --scope-prefix /services/canvas \
  --max-pages 6 \
  --out ./_outputs \
  --site-root auto
```

After the command finishes, inspect these artifacts:

- `_outputs/canvas/`
- `manifest.jsonl`
- `report.json`
- `toc.md`
- `report.html`

That is the proof layer this packet is built around:
one small, reviewable export with auditable output.
