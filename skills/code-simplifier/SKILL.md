---
name: code-simplifier
description: Simplifies and refines code for clarity, consistency, and maintainability while preserving all functionality. Analyzes recently modified code across three dimensions - code reuse, code quality, and efficiency - and provides actionable improvement suggestions. This skill should be used when the user asks to "simplify code", "refine code", "clean up code", "improve code quality", or requests a simplification review of recent changes.
triggers:
  - simplify
  - refine
  - cleanup
---

# Code Simplifier

Analyze recently modified code and suggest refinements that improve clarity, consistency, and maintainability - without changing what the code does. The review covers three complementary aspects:

1. **Code Reuse** - Eliminate duplication, consolidate shared logic, leverage existing utilities.
2. **Code Quality** - Improve naming, reduce complexity, enforce project standards from `AGENTS.md`.
3. **Efficiency** - Fix algorithmic issues, remove unnecessary work, optimize resource usage.

## Review Process

### Identify the Scope

Focus on code that has been recently modified or touched in the current session unless explicitly instructed to review a broader scope. Use `git diff` or the file list from the current PR/MR to determine the changed files.

### Sub-Agent Delegation (Preferred)

When sub-agent capability is available, delegate each review aspect to a separate sub-agent for parallel, focused analysis:

1. **Code Reuse Review Agent** - Read `references/code-reuse-review.md` and analyze the changed files for duplication and consolidation opportunities.
2. **Code Quality Review Agent** - Read `references/code-quality-review.md` and analyze the changed files for clarity, naming, complexity, and standards compliance.
3. **Efficiency Review Agent** - Read `references/efficiency-review.md` and analyze the changed files for performance and resource usage issues.

Each sub-agent should:
- Read the corresponding reference document for detailed criteria and output format
- Read `AGENTS.md` at the repository root for project-specific coding conventions
- Analyze only the recently changed code (unless instructed otherwise)
- Return findings in the format specified by its reference document

After all sub-agents complete, synthesize their findings into a single consolidated report.

### Sequential Review (Fallback)

When sub-agents are not available, perform all three reviews sequentially:

1. Read `references/code-reuse-review.md` - review for duplication and reuse
2. Read `references/code-quality-review.md` - review for clarity and standards
3. Read `references/efficiency-review.md` - review for performance and resources

Apply the criteria and output format from each reference document.

## Guiding Philosophy

- **Preserve Functionality**: Never change what the code does - only how it does it. All original features, outputs, and behaviors remain intact.
- **Follow Project Standards**: Apply the coding conventions from `AGENTS.md` at the repository root (import ordering, naming, module structure, error handling, component patterns).
- **Clarity Over Brevity**: Prefer explicit, readable code over compact one-liners. Avoid nested ternaries - use `if/else` or `switch` for multiple conditions.
- **Maintain Balance**: Avoid over-simplification that reduces clarity, creates overly clever solutions, or combines too many concerns into a single function.
- **Pragmatism**: Solve real problems, not imaginary ones. Do not optimize for theoretical edge cases or micro-benchmarks that do not matter at the project's scale.

## Consolidated Output Format

Present the combined results from all three review aspects:

```
## Code Simplification Review

### Scope
[List of files reviewed and how scope was determined]

### Code Reuse
[Findings from the reuse review, using **[REUSE]** tags]

### Code Quality
[Findings from the quality review, using **[QUALITY]** tags]

### Efficiency
[Findings from the efficiency review, using **[EFFICIENCY]** tags]

### Summary
[Overall assessment: is the code in good shape, or does it need significant refinement?]
[Prioritized list of the most impactful changes to make first]
```

When a review aspect has no findings, include it with an explicit "no issues found" statement rather than omitting the section.

## Reference Files

- **`references/code-reuse-review.md`** - Detailed criteria for detecting duplication, consolidation opportunities, and over-abstraction
- **`references/code-quality-review.md`** - Detailed criteria for naming, complexity, error handling, and project standards compliance
- **`references/efficiency-review.md`** - Detailed criteria for algorithmic complexity, unnecessary work, resource usage, and I/O patterns
