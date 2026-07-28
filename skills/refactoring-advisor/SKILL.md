---
name: refactoring-advisor
description: Analyze a codebase to identify structural problems and propose concrete refactoring plans using design patterns, dependency injection, and established refactoring techniques. This skill should be used when the user asks to "refactor", find "code smells" or "technical debt", simplify complex code, break up a "god class", reduce coupling or duplication, resolve circular dependencies, introduce dependency injection, improve testability, or create a refactoring plan for a function, class, module, package, or repository. Produce analysis and proposals only, without writing implementation code.
triggers:
  - refactor
  - code smells
  - technical debt
  - god class
  - spaghetti code
  - too coupled
  - hard to test
  - simplify
  - dependency injection
---

# Refactoring Advisor

Act as a senior software architect. Inspect the requested scope, diagnose structural causes, and produce an evidence-backed plan that a human or implementation agent can execute.

Do not modify production code, tests, configuration, or generated files. Do not provide implementation patches or full replacement code. Small pseudocode signatures or dependency diagrams are acceptable only when they clarify a proposed boundary.

## Core Principles

- Ground every finding in repository evidence. Cite file paths, symbols, and line ranges.
- Treat metric thresholds as investigation signals, not automatic defects.
- Diagnose causes and consequences before recommending patterns.
- Prefer the smallest refactoring that creates a meaningful boundary.
- Preserve externally observable behavior unless the user explicitly requests a behavior change.
- Evaluate dependency injection for every proposal. Recommend it when it moves volatile I/O, infrastructure, time, randomness, configuration, or external services behind an explicit boundary. State why it is unnecessary when direct dependencies are already stable and cohesive.
- Avoid adding interfaces, factories, layers, or patterns without a concrete consumer, testability need, or source of variation.
- Separate confirmed findings from hypotheses that require runtime data or owner input.

## Workflow

### 1. Establish Scope and Constraints

1. Read repository-level instructions such as `AGENTS.md`, `CONTRIBUTING.md`, and relevant package documentation.
2. Resolve the requested scope. For an unspecified request, inspect the whole repository while prioritizing production code and architectural boundaries.
3. Identify languages, frameworks, package boundaries, build systems, test layout, generated or vendored directories, and public APIs.
4. Exclude generated, vendored, dependency, build-output, fixture, and snapshot files unless they reveal an architectural boundary relevant to the request.
5. Record constraints that affect sequencing: compatibility promises, framework lifecycle, deployment topology, ownership, migrations, and test coverage.

Read `references/discovery.md` for repository mapping commands, language-specific cues, sampling strategy, and fallback methods. Use available static-analysis tools when the repository already provides them; do not install new tools merely to produce the report.

### 2. Discover Structural Signals

Inspect all relevant levels before drawing conclusions:

| Level | Signals to investigate |
| --- | --- |
| Function | More than roughly 50 lines, more than 4-5 parameters, nesting deeper than 3 levels, many branches, mixed I/O and domain logic, boolean control flags |
| Class | Too many responsibilities, low cohesion, many collaborators, feature envy, mutable global state, difficult construction, broad public surface |
| Module/package | Cycles, unstable boundaries, duplicated policies, leaky abstractions, shotgun changes, unrelated exports, infrastructure mixed with domain logic |
| Cross-cutting | Service locator use, hidden dependencies, inconsistent error handling, repeated validation, scattered configuration, temporal coupling, untestable side effects |

Corroborate each signal with at least one consequence, such as change amplification, fragile tests, duplicated fixes, unclear ownership, runtime risk, or blocked reuse. Do not report long code or a high count alone as a smell.

Build a compact evidence inventory before prioritizing. Include:

- exact path and symbol;
- narrow line range or call sites;
- dependency direction and affected consumers;
- tests that cover or fail to isolate the area;
- confidence level: high, medium, or low.

### 3. Diagnose Root Causes

Map each material finding to one or more named smells from `references/smells-and-strategies.md`. Distinguish the visible symptom from the architectural cause.

For each finding:

1. State the observed evidence.
2. Name the smell.
3. Explain the root cause and why the current boundary permits it.
4. Describe the maintenance, testability, reliability, or delivery impact.
5. Note uncertainty or missing evidence.

Merge findings that share one root cause. Do not inflate the report with multiple symptoms of the same dependency problem.

### 4. Design Refactoring Proposals

Create one proposal per independently executable change. Each proposal must include:

1. **Target and evidence** - exact files, symbols, and line ranges.
2. **Desired boundary** - named functions, classes, modules, interfaces, or packages to extract, move, split, or replace.
3. **Step sequence** - behavior-preserving steps small enough for incremental review.
4. **Dependency injection evaluation** - recommend constructor, parameter, factory, or framework-native injection when applicable; otherwise state `Not needed` with a specific reason.
5. **Pattern choice** - name a design or refactoring pattern only when it solves the diagnosed problem; explain why it fits better than a simpler extraction.
6. **Behavior and API constraints** - contracts that must remain stable.
7. **Verification** - existing tests to run and focused characterization, unit, integration, or architecture tests to add.
8. **Risks and rollback boundary** - likely regressions, migration concerns, and a safe commit boundary.
9. **Effort and impact** - low, medium, or high, with a short rationale.

Prefer dependency direction from policy toward abstractions, with infrastructure implementing those abstractions. Keep domain logic independent of frameworks where the repository's architecture supports that separation. Do not recommend a dependency injection container when explicit constructor or parameter injection is sufficient.

### 5. Prioritize the Plan

Rank proposals by impact, confidence, dependency order, and effort. Put enabling characterization tests or cycle-breaking boundaries before broad extractions. Identify quick wins separately from foundational work, and call out proposals that should not proceed until a hypothesis is verified.

Use `references/report-template.md` exactly for the final report. Include every section even when no material issues are found. In that case, document the inspected scope, evidence, and residual risks rather than inventing findings.

## Quality Gate

Before returning the report, verify that:

- Discovery covered functions, classes, modules or packages, and cross-cutting concerns.
- Every finding names a recognized smell and cites concrete evidence.
- Every proposal names affected paths and symbols, not generic layers such as "add a service".
- Every proposal contains an explicit dependency injection decision.
- Proposed steps preserve behavior and are independently verifiable.
- The action plan reflects prerequisites and impact versus effort.
- No implementation code, patch, or unrequested file modification was produced.

## References

- `references/discovery.md` - Repository scanning, evidence collection, language cues, and large-repository sampling
- `references/smells-and-strategies.md` - Named smells, root-cause prompts, DI guidance, and fitting strategies
- `references/report-template.md` - Required output structure for findings, proposals, and prioritized actions
