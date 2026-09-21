---
name: custom-codereview-guide
description: Repository-specific code review guidelines for OpenHands/extensions
triggers:
- /codereview
---

# Extensions Repo — Code Review Guidelines

## Repository Boundaries

Review whether a PR belongs in this public extensions registry. Skills, plugins, automations, and integrations belong here; Agent Server behavior, API endpoints, and typed browser API access under `clients/typescript/` belong in [`OpenHands/software-agent-sdk`](https://github.com/OpenHands/software-agent-sdk), UI belongs in [`OpenHands/OpenHands`](https://github.com/OpenHands/OpenHands), and scheduling/dispatch lifecycle behavior belongs in [`OpenHands/automation`](https://github.com/OpenHands/automation).

If a PR is opened in the wrong repository, explicitly recommend that it may need to be closed and moved to the repository that owns the change rather than merged here. Apply the repository's contribution and review guidance to every PR.

## Design Docs for Deep PRs

A diff shows line-level edits, not always the design: intent, contract shape,
before/after behavior, compatibility, and why the approach fits. Expect concise
design context for a deep PR that a reviewer cannot fully judge from the diff in
a couple of minutes, for example:

- a new or changed skill, plugin, automation, integration contract, or manifest
  schema;
- a new subsystem, cross-cutting refactor, or migration;
- a behavior change in shared loading, validation, discovery, or execution; or
- a large diff whose intent is difficult to hold at once after generated files,
  lockfiles, snapshots, vendored code, and mechanical churn are excluded.

Skip this for trivial or self-explanatory changes such as typos, one-line guards,
dependency bumps, small documentation edits, and localized fixes. Line count is
a signal, never a gate by itself.

When a deep PR lacks adequate design context, weigh the omission against risk:

- **🔴 HIGH risk:** do not approve. Submit **COMMENT** and request design context
  before a human merge decision.
- **🟡 MEDIUM risk:** use judgment; withhold approval when reconstructing the
  design from the diff would materially slow or weaken review.
- **🟢 LOW risk:** never block solely on missing design context.

Design context may be an available design-doc artifact or a durable write-up in
the PR description. An equivalent write-up must state the intent, important
before/after behavior or contract shape, compatibility and risk, and grounded
code references.

The `.pr/` workflow removes temporary artifacts after a same-repository approval.
If a temporary `.pr/` page is the primary design explanation, do not submit an
automated approval until a human maintainer has reviewed it, unless the PR
already contains the durable equivalent context above. Leave a **COMMENT** so the
artifact remains available for the human decision.

A design doc aids review; it does not excuse correctness, security, architecture,
or repository-ownership problems.

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
