# PkgDiet Dependency Policy & Health Guardrail

Evaluates npm packages using the PkgDiet MCP server before they are installed or recommended in OpenHands.

## Features

- **Pre-install evaluation**: Gates `npm install`, `pnpm add`, `yarn add`, or `bun add` commands.
- **ALLOW / WARN / BLOCK verdicts**: Enforces dependency quality, maintenance health, and bloat thresholds.
- **Alternatives suggestion**: Proactively suggests modern alternatives when a package is deprecated or bloated via `suggest_alternative`.

## Usage

When the PkgDiet MCP server is configured in OpenHands:
- Before adding dependencies, the agent invokes `check_dependency` or `check_dependencies`.
- If blocked, the agent retrieves safe alternatives and requests user consent before proceeding.

Note: PkgDiet acts as a policy and supply-chain health guardrail based on metadata and configured policies; it is not a standalone malware scanner.
