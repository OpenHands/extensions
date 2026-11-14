---
name: pkgdiet
description: Evaluates npm packages with the PkgDiet MCP server and surfaces ALLOW/WARN/BLOCK policy verdicts before installation.
---

# Dependency Management Policy

You have access to the `pkgdiet` MCP server. Whenever you are about to suggest or run an `npm install`, `yarn add`, `pnpm add`, or `bun add` command, you MUST follow these rules:

1. **Pre-Check:** Call the `check_dependency` tool on every package you intend to install (or `check_dependencies` when evaluating multiple packages).
2. **Handle ALLOW:** If the verdict is ALLOW, you may proceed with the installation.
3. **Handle WARN:** If the verdict is WARN, inform the user of the health score, bloat, or policy warnings. Call `suggest_alternative` to find a modern replacement, and ask the user if they want to proceed or use an alternative.
4. **Handle BLOCK:** If the verdict is BLOCK, you MUST NOT install the package. Call the `suggest_alternative` tool to find a modern replacement, and ask the user for permission to install the replacement instead.

Note: PkgDiet is a policy and dependency health guardrail evaluating metadata and thresholds; it does not guarantee against unknown CVEs or malicious package behavior.
