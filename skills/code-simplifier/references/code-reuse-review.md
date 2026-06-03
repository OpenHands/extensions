# Code Reuse Review

A detailed reference for analyzing code reuse opportunities in recently modified code. Focus on reducing duplication, improving shared abstractions, and consolidating related logic - without over-abstracting or sacrificing readability.

## Core Principles

1. **DRY (Don't Repeat Yourself)**: Repeated logic, patterns, or data transformations across files or functions indicate missing abstractions.
2. **Extract, Don't Abstract Prematurely**: Share concrete, well-understood patterns. Avoid creating generic frameworks for two-use-case scenarios.
3. **Respect AGENTS.md Standards**: Follow the project's established conventions (found in `AGENTS.md` at the repository root) for module structure, import ordering, and shared utility placement.
4. **Preserve Functionality**: Refactoring for reuse must not change behavior. All original features, outputs, and edge-case handling remain intact.

## What to Look For

### Duplicate Code Blocks

- Near-identical functions or methods across files
- Copy-pasted logic with minor parameter differences
- Repeated validation, parsing, or formatting routines
- Similar error-handling patterns that could share a utility

### Missing Shared Utilities

- String manipulation, date formatting, or data transformation repeated in multiple places
- Configuration or constant values hard-coded in several files instead of centralized
- Common I/O patterns (file reading, HTTP requests, DB queries) reimplemented per call site

### Consolidation Opportunities

- Multiple functions that do slight variations of the same task - candidates for a single parameterized function
- Related helper functions scattered across modules that belong in a shared utility module
- Inline lambdas or closures duplicated across components

### Over-Abstraction (Anti-Pattern)

- Shared base classes or generic wrappers introduced for only one or two consumers
- Abstraction layers that obscure simple operations
- "Util" modules that become dump-grounds for unrelated functions

## Review Checklist

- [ ] Identify all blocks of duplicated or near-duplicated code in the changed files
- [ ] For each duplicate, determine whether extraction into a shared function/module is warranted (≥ 3 occurrences or high maintenance risk)
- [ ] Verify the project already has a utility or helper module; suggest placement there when it exists
- [ ] Confirm the proposed extraction preserves all call-site behavior
- [ ] Check that new shared code follows the naming and structure conventions in `AGENTS.md`
- [ ] Flag any existing abstractions in the codebase that the new code could leverage instead of reimplementing

## Output Format

For each reuse finding, provide:

```
**[REUSE]** [file:line] - Brief description
  Duplicated in: [other-file:line], [another-file:line]
  Suggestion: Extract to `shared/utils.ts#functionName` (or appropriate module)
  Impact: Reduces maintenance surface, single source of truth for [logic description]
```

When no actionable reuse findings exist, state explicitly:

```
**[REUSE]** No significant duplication detected in the changed files.
```
