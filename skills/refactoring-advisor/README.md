# Refactoring Advisor

Analyze a codebase for structural problems and produce an evidence-backed refactoring plan without changing code.

## What It Covers

- Function-level complexity and mixed responsibilities
- Class cohesion, collaborator count, and construction problems
- Module and package boundaries, including circular dependencies
- Cross-cutting concerns such as hidden dependencies, duplicated policy, configuration, and untestable side effects
- Dependency injection decisions for every proposal
- Prioritization by impact, effort, confidence, and prerequisite order

The skill supports Java, Python, TypeScript, and C# with language-specific discovery guidance. It treats size and complexity thresholds as investigation signals rather than automatic defects.

## Usage

Ask OpenHands to audit a repository or a narrower scope, for example:

- "Scan this repository for code smells and create a refactoring plan."
- "These modules are too coupled. How should we separate them?"
- "Make this service easier to test with dependency injection."
- "Diagnose the circular dependencies in this package."

The output contains a scope statement, architecture snapshot, evidence-linked findings, independently executable proposals, an explicit dependency injection evaluation for each proposal, and a prioritized implementation handoff.

## Skill Resources

- `SKILL.md` defines the analysis workflow and quality gate.
- `references/discovery.md` describes repository scanning and language-specific cues.
- `references/smells-and-strategies.md` maps named smells to refactoring and DI strategies.
- `references/report-template.md` defines the required report structure.
