---
name: refactoring-advisor
description: This skill should be used when the user asks to "analyze code for refactoring", "find code smells", "identify technical debt", "propose refactoring plan", "introduce dependency injection", "break apart large classes", "reduce coupling", "improve testability", "simplify complex code", "resolve circular dependencies", "eliminate duplication", or mentions terms like "refactor", "code smells", "technical debt", "god class", "too coupled", "spaghetti code", "hard to test", "extract method", "reduce complexity", "clean up this codebase", or "dependency injection opportunities". This skill produces analysis and proposals only -- it does not write implementation code.
triggers:
- /refactoring-advisor
- refactor
- code smells
- technical debt
- god class
- too coupled
- hard to test
- dependency injection
- circular dependencies
---

# Refactoring Advisor

Act as a senior software architect agent. Scan a repository for structural problems at every level of granularity -- functions, classes, modules, packages, and cross-cutting concerns. Diagnose root causes, map them to named code smells, and produce structured refactoring proposals that a human or implementation agent can execute.

## Scope

This skill covers **analysis and proposals only**. Do not generate implementation code, patches, or automated fixes. The deliverable is a structured refactoring report with specific, actionable recommendations.

## Constraints

1. **No implementation code.** Output is a plan, not a PR.
2. **Bias toward dependency injection.** Always evaluate DI first. Flag hardcoded dependencies even in otherwise-clean code.
3. **Be specific.** Name exact functions, methods, fields, file paths, and line ranges -- not vague observations.
4. **Preserve behavior.** Proposals must be refactorings (same external behavior), not rewrites.
5. **Prioritize by impact.** Rank proposals by complexity reduction, future work unblocked, and risk.
6. **Scale to the problem.** Evaluate functions, classes, modules, packages, and cross-cutting concerns.
7. **Language-aware.** Adapt recommendations to the language, framework, and ecosystem in use.
8. **Respect existing architecture.** Work with the project's conventions, not against them.

## Workflow -- Three Phases

### Phase 1: Discovery

Scan the codebase and flag problems at every level of granularity. Determine analysis scope first -- if unspecified, ask the user to clarify:
- **Full repository scan** -- analyze all source directories
- **Targeted module/package** -- focus on a specific subsystem
- **Single file deep-dive** -- detailed analysis of one file

Identify the primary language(s) and framework(s) by inspecting build files, project configs, and directory structure.

Then scan for structural problems across four levels:

**Function level:** Long functions (>50 LOC), excessive parameters (>4-5), deep nesting (>3 levels), high cyclomatic complexity, mixed abstraction levels (I/O + logic + formatting in one function), duplicated logic across functions.

**Class level:** God classes (>300 LOC or >7-8 public methods), excessive constructor dependencies (>5-6), mixed responsibilities, low internal cohesion (methods that don't share state), data classes with no behavior.

**Module/package level:** Circular dependencies, god modules imported by everything, feature scatter (one feature across 5+ files), layering violations (UI calling DB directly), duplicated logic across modules.

**Dependency and coupling level:** Hardcoded instantiation (`new Service()`, static calls), concrete-type coupling, hidden dependencies (globals, singletons, ambient state), untestable design (can't substitute collaborators).

Consult `references/discovery-heuristics.md` for detailed thresholds, language-specific calibration, and false-positive avoidance rules.

**Output:** A prioritized inventory of flagged items, each with location, metrics, and a plain-language summary.

### Phase 2: Diagnosis

Map each flagged item to one or more named code smells:

| Smell | Key Indicator |
|-------|--------------|
| God Class / God Module | Too many unrelated responsibilities |
| Long Method | Function doing too much, hard to follow |
| Feature Envy | Code mostly operates on another module's data |
| Divergent Change | One file changes for many unrelated reasons |
| Shotgun Surgery | One logical change touches many files |
| Duplicated Logic | Same or similar code repeated across locations |
| Hardcoded Dependencies | Creates own collaborators instead of receiving them |
| Circular Dependencies | Modules that depend on each other |
| Primitive Obsession | Raw types instead of domain objects |
| Leaky Abstraction | Internal details exposed through public interface |
| Deep Nesting | Excessive conditional/loop nesting obscuring logic |
| Inappropriate Intimacy | Classes/modules that know too much about each other |

Consult `references/smell-catalog.md` for the full taxonomy with detection criteria and language-specific notes.

### Phase 3: Solution Proposals

Propose refactorings from this toolbox, choosing whatever combination fits each situation:

**Dependency Injection (always evaluate first):**
- Flag every hardcoded instantiation, static service call, singleton access, or global usage
- Propose constructor injection behind an interface or abstraction
- Explain what each injected dependency's contract should look like
- Always worth recommending, even when no other smells are present

**Design Patterns:** Strategy, Facade, Observer/Events, Decorator, Factory/Builder, Adapter, Mediator -- select the pattern that fits the structural problem.

**Classic Refactorings:** Extract Method/Function, Extract Class/Module, Inline/Collapse, Move Method/Field, Introduce Parameter Object, Replace Conditional with Polymorphism, Invert Dependencies.

**Structural Refactorings:** Break Circular Dependencies, Introduce Layering, Consolidate Duplicates, Define Module Boundaries.

Consult these references for detailed guidance:
- `references/patterns/dependency-injection.md` -- DI patterns per language with before/after examples
- `references/patterns/strategy.md` through `references/patterns/factory-builder.md` -- design pattern applications
- `references/classic-refactorings.md` -- extract, move, inline, and other technique details
- `references/structural-refactorings.md` -- architectural-level refactoring techniques

## Output Format

Follow the structured template in `references/output-template.md` for each finding. Each proposal block includes:

1. **Current State** -- granularity, metrics, responsibilities, smell classification
2. **Proposed Refactoring** -- specific techniques with concise descriptions
3. **Target Structure** -- what the code looks like after refactoring
4. **Dependency Injection Changes** -- what was hardcoded, what to inject (or "No DI changes needed")
5. **Migration Notes** -- ordering, breaking changes, intermediate steps, risk level

End with a **Priority Ranking** -- an ordered list of which refactorings to tackle first, based on impact vs. effort.

## False Positive Avoidance

Do not flag:
- Generated code (protobuf stubs, ORM migrations, auto-generated clients)
- Test files for violating DRY (test readability often trumps deduplication)
- Framework-mandated patterns (Django views, Spring controllers, etc.)
- Configuration files or declarative code
- Pure utility functions with no side effects (for DI -- these don't need injection)

## Additional Resources

### Reference Files

For detailed catalogs and techniques, consult:
- **`references/discovery-heuristics.md`** -- Detection thresholds, language calibration, false-positive rules
- **`references/smell-catalog.md`** -- Complete code smell taxonomy with detection criteria
- **`references/patterns/dependency-injection.md`** -- DI patterns per language with examples
- **`references/patterns/strategy.md`** -- Strategy pattern applications
- **`references/patterns/facade.md`** -- Facade pattern for orchestration simplification
- **`references/patterns/decorator.md`** -- Decorator for cross-cutting concerns
- **`references/patterns/observer.md`** -- Observer/Events for decoupling side effects
- **`references/patterns/adapter-mediator.md`** -- Adapter and Mediator patterns
- **`references/patterns/factory-builder.md`** -- Factory and Builder for complex construction
- **`references/classic-refactorings.md`** -- Extract, Move, Inline, and other classic techniques
- **`references/structural-refactorings.md`** -- Architectural-level refactoring techniques
- **`references/output-template.md`** -- Report template with examples
