# Code Quality Review

A detailed reference for evaluating code clarity, consistency, and maintainability in recently modified code. Focus on structural simplicity, naming, readability, and adherence to project standards — while preserving all existing functionality.

## Core Principles

1. **Clarity Over Brevity**: Explicit, readable code is better than clever one-liners. Avoid nested ternaries, dense chaining, or overly compact expressions that sacrifice understanding.
2. **Structural Simplicity**: Reduce nesting, eliminate unnecessary abstractions, and consolidate related logic. If a function needs more than three levels of indentation, redesign it.
3. **Consistent Standards**: Follow the project's coding conventions documented in `AGENTS.md` at the repository root — import ordering, naming patterns, module structure, error handling style, and component patterns.
4. **Preserve Functionality**: Quality improvements must not alter behavior. All outputs, side effects, and edge-case handling remain unchanged.

## What to Look For

### Naming and Intent

- Variables, functions, and classes that fail to communicate their purpose
- Abbreviated or single-letter names outside trivial loop counters
- Boolean variables or functions without `is`/`has`/`should`/`can` prefixes where appropriate
- Generic names like `data`, `result`, `temp`, `item` when a domain-specific name exists
- Inconsistent naming style within the same module (camelCase mixed with snake_case, etc.)

### Complexity and Nesting

- Functions with more than three levels of indentation
- Long functions doing multiple unrelated things (violating single responsibility)
- Complex conditional chains that could be simplified with early returns, guard clauses, or lookup tables
- Nested ternary operators — always prefer `if/else` or `switch` for multiple conditions
- Deeply nested callbacks or promise chains that could be flattened

### Redundancy and Dead Code

- Unused imports, variables, or parameters
- Commented-out code left in production files
- Redundant null checks, type assertions, or defensive code that the type system or caller contract already guarantees
- Unnecessary intermediate variables that add no clarity
- Comments that restate what the code obviously does

### Error Handling

- Swallowed exceptions (empty `catch` blocks or `except: pass`)
- Overly broad catch clauses that mask real failures
- Missing error context (re-raising without original cause)
- Try/catch wrapping logic that cannot fail
- Inconsistent error handling strategy across the module

### Project Standards Compliance

- Import ordering and grouping per `AGENTS.md`
- Module/function export patterns consistent with the project
- Proper type annotations where the project requires them
- React component patterns (if applicable): explicit Props types, proper hook usage
- File and directory organization matching project conventions

## Review Checklist

- [ ] Read `AGENTS.md` to understand project-specific conventions before reviewing
- [ ] Verify all new/modified names clearly communicate intent
- [ ] Check that no function exceeds three levels of nesting
- [ ] Confirm each function has a single clear responsibility
- [ ] Flag any nested ternaries or dense one-liners that harm readability
- [ ] Identify unused code, redundant checks, and stale comments
- [ ] Verify error handling is consistent and informative
- [ ] Confirm adherence to project coding standards from `AGENTS.md`
- [ ] Ensure inline documentation exists for non-obvious logic (but not for obvious code)

## Output Format

For each quality finding, provide:

```
**[QUALITY]** [file:line] — Brief description
  Issue: [What is wrong and why it matters]
  Suggestion: [Concrete, actionable improvement]
  Severity: CRITICAL | IMPROVEMENT | MINOR
```

Severity guide:
- **CRITICAL**: Actively harms maintainability, hides bugs, or violates project standards in a way that will cause problems.
- **IMPROVEMENT**: Code works but could be meaningfully cleaner, clearer, or more consistent.
- **MINOR**: Cosmetic or stylistic; mention only when it genuinely impacts readability. Do not nitpick.

When code quality is already good, state explicitly:

```
**[QUALITY]** Code is clean, well-structured, and follows project conventions. No issues found.
```
