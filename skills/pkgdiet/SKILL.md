---
name: pkgdiet
description: Evaluates npm packages with the PkgDiet MCP server and surfaces ALLOW/WARN/BLOCK policy verdicts before installation.
---

# Dependency Management Policy

When the `pkgdiet` MCP server is configured and available, follow these guidelines before suggesting or executing package installations (`npm install`, `yarn add`, `pnpm add`, or `bun add`):

1. **Availability Check:** Check if the `check_dependency` MCP tool is available. If the PkgDiet MCP server is not connected or the tool is unavailable, inform the user and continue with the standard installation workflow normally.
2. **Pre-Check:** When available, call the `check_dependency` tool on each package you intend to install (or `check_dependencies` for batch evaluations).
3. **Handle ALLOW:** If the verdict is ALLOW, proceed with the installation.
4. **Handle WARN:** If the verdict is WARN, inform the user of the health score, bloat, or policy warnings. Call `suggest_alternative` to find a modern replacement, and ask the user if they want to proceed or use an alternative.
5. **Handle BLOCK:** If the verdict is BLOCK, explain the reasons to the user and call `suggest_alternative` to find modern, maintained alternatives. Do not install by default, but allow the user to explicitly confirm an override if they still wish to proceed.

Note: PkgDiet acts as a policy and dependency health guardrail evaluating npm metadata and configured thresholds. It does not replace code audits or guarantee against unknown vulnerabilities.
