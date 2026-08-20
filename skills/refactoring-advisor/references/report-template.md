# Required Report Template

Use this structure exactly. Replace bracketed instructions and omit no top-level section.

```markdown
# Refactoring Assessment

## Executive Summary

[Summarize the architectural condition, highest-value intervention, and important constraints in 3-6 sentences.]

## Scope and Method

- Scope requested: [repository, package, module, class, function, or changed files]
- Inspected: [paths, entry points, tests, and dependency/build metadata]
- Excluded: [generated, vendored, out-of-scope, or uninspected areas]
- Method: [commands, existing analyzers, dependency traces, and sampling]
- Constraints: [compatibility, framework lifecycle, ownership, deployment, or unknowns]

## Architecture Snapshot

[Describe current boundaries and dependency direction. Include a compact text or Mermaid diagram only when it materially clarifies at least three components.]

## Findings

### F1 - [Specific finding title]

- Severity: Critical | High | Medium | Low
- Confidence: High | Medium | Low
- Scope: Function | Class | Module/Package | Cross-cutting
- Smell: [recognized smell name]
- Evidence: `[path:start-end]` - `[symbol]`; [related call sites, dependencies, or tests]
- Root cause: [why the current boundary produces the symptom]
- Consequence: [maintenance, testability, reliability, performance, or delivery impact]
- Uncertainty: [missing runtime or ownership evidence, or `None`]

[Repeat only for material findings. If none exist, state that explicitly and summarize residual risk.]

## Refactoring Proposals

### P1 - [Outcome-oriented proposal title]

- Addresses: [F1, F2]
- Target: `[paths and symbols]`
- Desired boundary: [specific functions, classes, modules, interfaces, or packages]
- Refactoring strategy: [named refactoring operations and justified design pattern, if any]
- DI evaluation: [Constructor | Parameter | Factory | Framework-native | Not needed] - [specific rationale]
- Behavior/API constraints: [contracts to preserve]
- Effort: Low | Medium | High - [rationale]
- Impact: Low | Medium | High - [rationale]
- Risks: [regression and migration risks]
- Verification: [existing tests plus focused tests or architecture checks to add]
- Rollback boundary: [independently revertible commit or compatibility seam]

Steps:

1. [Small, behavior-preserving step naming concrete symbols.]
2. [Next step.]
3. [Verification or cutover step.]

[Repeat for each independently executable proposal.]

## Prioritized Action Plan

| Order | Proposal | Prerequisites | Impact | Effort | Why now |
| --- | --- | --- | --- | --- | --- |
| 1 | P# | [none or proposal/test] | High | Low | [reason] |

### Quick Wins

- [Low-effort, evidence-backed actions.]

### Foundational Work

- [Boundary or test work that enables later proposals.]

### Defer or Validate First

- [Low-confidence or poor cost/benefit proposals and required evidence.]

## Implementation Handoff

- Suggested change sequence: [review-sized stages]
- Characterization coverage needed first: [specific behavior and tests]
- Decisions requiring owner input: [API, data, ownership, or deployment decisions]
- Definition of done: [observable structural and testability outcomes]
```

## Evidence Rules

- Use repository-relative paths and 1-based line ranges.
- Keep ranges narrow enough to locate the relevant code.
- Name symbols and affected callers when possible.
- Label inferences as inferences.
- Do not paste code blocks, executable pseudocode, or implementation-ready replacements.
- Keep finding IDs and proposal IDs stable so an implementation agent can reference them.
