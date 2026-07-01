---
name: custom-codereview-guide
description: Repository-specific code review guidelines for OpenHands/extensions
triggers:
- /codereview
---

# Extensions Repo — Code Review Guidelines

## SDK Documentation Placement

If a PR adds or modifies OpenHands SDK-specific documentation (API guides, SDK usage examples, SDK feature descriptions), flag it:

- The canonical source of truth for SDK documentation is <https://docs.openhands.dev/sdk> and its `llms.txt` index.
- The `skills/openhands-sdk/SKILL.md` in this repo is a thin pointer to the docs site. It should NOT contain duplicated SDK content.
- **Push back**: ask the submitter to contribute SDK documentation changes to [OpenHands/docs](https://github.com/OpenHands/docs) instead.

## Pre-release Integration Catalog Changes

The `@openhands/extensions/mcps` catalog was experimental and pre-release. If a
PR intentionally replaces it with the broader `integrations` catalog and updates
known downstream consumers in the same coordinated stack, do not require
backward-compatible `mcps` aliases or a deprecation window. Require migration
documentation for consumers, but accept a clean breaking change for this
pre-release surface.
