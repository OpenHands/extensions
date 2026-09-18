---
name: custom-codereview-guide
description: Repository-specific review guidance for OpenHands/extensions.
triggers:
- /codereview
---

# OpenHands/extensions review guide

Apply this guide with the general code-review skill and `AGENTS.md`. Approve the
current head when it has no material correctness, security, compatibility, or
acceptance-criterion defect. Comment only on concrete failures; do not withhold
approval for optional refactors, tone, style, or speculative improvements.

## Repository ownership and scope

This repository owns reusable skills, plugins, automation bundles, and integration
catalogs. Agent Server behavior, endpoints, and browser client code belong in
`OpenHands/software-agent-sdk`; Canvas UI belongs in `OpenHands/OpenHands`; and
scheduling, dispatch, run history, and sandbox lifecycle belong in
`OpenHands/automation`.

A content PR should remain focused on one extension or one shared mechanism that
multiple extensions actually use. Flag unrelated edits to another skill, plugin,
or automation. Shared runtime machinery belongs in the owning product repository,
not copied into extension content.

## Blocking checkpoints

### Executable instructions and runtime parity

Commands, imports, environment variables, endpoints, and setup steps in extension
content are executable contracts. Verify them against the released packages and
the actual local and cloud environments that claim support. Do not approve an
example that relies on an unreleased API, a developer-only dependency, a private
path, or a variable that the production runtime does not provide.

For a changed skill, plugin, hook, or automation, follow its documented entrypoint
in a clean environment far enough to exercise the changed behavior. Keep local
and cloud behavior identical unless the documentation names and explains a real
platform capability difference.

### Untrusted triggers and credentials

Treat repository events, issue and PR comments, chat messages, catalog fields,
and extension-provided arguments as untrusted. Verify who may trigger the action,
whose identity it runs as, which repository or organization it can affect, and
which secrets it receives. A trigger phrase alone is not authorization. Require
an explicit allowlist, permission check, or repository policy before performing
mutating or credentialed work.

Use only the minimum documented credential set. Never place secret values in
prompts, logs, generated files, examples, or persisted state.

### Sources of truth and generated artifacts

Identify the hand-authored source before reviewing a catalog or generated file.
A change should update that source once and regenerate every derived artifact
with the repository's existing sync/build command. Documentation must describe
the real direction of generation; do not call a generated asset the source of
truth or claim two runtimes read one asset when they do not.

Check the marketplace entry and generated command/catalog coverage required by
`AGENTS.md`. Do not add a parallel catalog, provider-specific copy, or manual
compatibility layer when the repository already has a generator or schema.

### Documentation claims

Test copy-paste commands and verify named tools, flags, package exports, URLs, and
installation mechanisms from authoritative sources. A plausible command is not
evidence. Documentation that teaches the wrong data flow or setup is a material
finding because agents execute it directly.

SDK documentation belongs in `docs.openhands.dev/sdk`; the generated
`skills/openhands-sdk/SKILL.md` remains a thin synchronized entrypoint. The
former `@openhands/extensions/mcps` catalog was experimental and pre-release, so
an explicitly coordinated replacement with the `integrations` catalog needs
consumer migration documentation but not compatibility aliases or a deprecation
window.

### Dependencies and supply chain

Apply the general seven-day release-recency guard to the exact dependency version,
regardless of the package's age or popularity. Validate installation with the
package manager and runtime used by the extension. Temporary git pins and
unreleased package APIs are blockers for merge unless the PR is an explicit,
coordinated stack that will replace them before release.

## Evidence and comment discipline

Evidence should exercise the extension as users invoke it: run the command, hook,
plugin, or automation entrypoint and show the relevant result. Static text checks
alone do not validate executable instructions. Require only the environments and
paths the change affects.

Do not comment on punctuation, preferred prose tone, optional DRY cleanup, or
hypothetical non-standard configurations without a supported failure mode. Before
raising a finding, verify that the referenced file and behavior are present in
the current PR head and have not already been addressed in review history.
