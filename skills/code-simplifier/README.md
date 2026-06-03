# Code Simplifier

A code simplification skill that analyzes recently modified code and suggests refinements across three dimensions:

| Aspect | Reference | Focus |
|--------|-----------|-------|
| **Code Reuse** | `references/code-reuse-review.md` | Duplication, shared utilities, consolidation |
| **Code Quality** | `references/code-quality-review.md` | Naming, complexity, readability, standards |
| **Efficiency** | `references/efficiency-review.md` | Algorithms, resource usage, unnecessary work |

## How It Works

The skill reviews recently changed code (via `git diff` or PR file list) and produces a consolidated report with tagged findings (`[REUSE]`, `[QUALITY]`, `[EFFICIENCY]`).

When sub-agents are available, each aspect is delegated to a separate agent for parallel, focused analysis. Otherwise, the review is performed sequentially.

## Adapted From

This skill is adapted from the [code-simplifier plugin](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/code-simplifier) in the Claude Plugins Official repository. Key adaptations:

- Split into three focused review aspects (reuse, quality, efficiency) instead of a single pass
- References project conventions via `AGENTS.md` instead of `CLAUDE.md`
- Supports sub-agent delegation for parallel review
- Uses progressive disclosure with reference documents

## Usage

Trigger phrases: "simplify code", "refine code", "clean up code", "improve code quality", or request a simplification review of recent changes.

The skill reads `AGENTS.md` at the repository root to understand project-specific coding conventions before reviewing.
