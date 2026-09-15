# Actual npm archive verification

September 13, 2026. [Recorded results](npm-archives.json) identify the exact main and composed factory source commits.

From clean source checkouts, ran `npm pack --ignore-scripts --json` before and after the workflow's release staging operation:

```bash
mkdir -p "$RUNNER_TEMP/extensions-package"
cp -RL . "$RUNNER_TEMP/extensions-package/"
```

Packed the staged directory, extracted its real tarball, and compared resource bytes with the canonical source. Main's `skills/github/.claude-plugin/plugin.json` and the four composed factory `scripts/github_client.py` resources were absent before staging. After staging, each was an ordinary file with identical contents. All four standalone workers imported successfully from the extracted npm package in an environment with their SDK dependencies installed. Package sizes were approximately 1.1–1.2 MB.

`cp -aL` was also tried and rejected: preserving hard-link identity led to malformed hard links with npm 11.6.2 and an internal packaging failure with npm 11.18.0. `cp -RL` creates independent regular files and passed actual archive extraction/imports.

This verifies release artifacts, not a changed Canvas interface. Raw `npm pack` from the linked source checkout still omits links; the production release workflow packs and publishes its materialized copy consistently. No npm release was published during validation. The functional change is confined to release staging; no loader, runtime, or fallback import code was introduced.
