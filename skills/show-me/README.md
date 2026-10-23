# Show Me

Help the user understand the current topic visually with concise diagrams,
code-shape sketches, diffs, and focused HTML artifacts. Pick the smallest view
that explains the point; keep the surrounding prose brief.

## Use

Ask OpenHands to show how something works, explain a change visually, or sketch
component and module boundaries. The skill supports pseudocode, call trees,
component trees, file trees, Mermaid diagrams, diffs, and HTML. It does not
require an MCP server, a paid service, or extra runtime dependencies.

The marketplace marks this skill `defaultEnabled: true`. Hosts can use
`DEFAULT_ENABLED_SKILL_NAMES` to seed new workspaces. This does not overwrite
existing saved skill selections or force an opt-in on existing workspaces.

## Upstream and license

Vendored from HumanLayer's [show-me skill](https://github.com/humanlayer/humanlayer/blob/3a8dd2d3c1ed01d4fd2282b6dee2075199dffffb/apps/riptide-humanlayer-claude-plugin/skills/show-me/SKILL.md) at commit `3a8dd2d3c1ed01d4fd2282b6dee2075199dffffb`.
The original file's SHA-256 is
`968f25af5bce778c06826f5bc4540631c3eab3e067be0fe48b48552cc1664a1f`.

Copyright 2025-2026 QueryTale, Inc. d/b/a HumanLayer. Licensed under Apache-2.0.
The upstream [LICENSE](LICENSE) and [NOTICE](NOTICE) are retained here.

Local modifications:

- Add the Apache-2.0 license identifier to the skill frontmatter.
- Replace HumanLayer's `.humanlayer/tasks/` path and `task-artifact` renderer
  instruction with host-supported workspace artifact links or previews. Follow
  repository sharing rules and require permission before externally publishing
  private content.
- Add OpenHands marketplace/plugin metadata and this provenance document.

The visual explanation examples and the remaining skill instructions are
unchanged. This import is independent of other skills with the same name.
