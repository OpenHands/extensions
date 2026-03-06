# Output Template

Structured template for Phase 3 output. Follow this format for every finding and for the overall report.

## Report Structure

```
## Refactoring Report: [Repository/Module Name]

### Executive Summary
- **Scope**: [Full repo / module name / file name]
- **Language(s)**: [Primary language and framework]
- **Items flagged**: [count] ([critical]/[moderate]/[minor])
- **Top priority**: [1-sentence summary of highest-priority finding]

### Findings

[Proposal blocks -- one per finding, ordered by priority]

### Priority Ranking

[Ordered action plan table]

### Recommendations Summary

[2-3 paragraph overview of the most impactful changes, suggested sequencing,
 and any risks or prerequisites for the refactoring effort.]
```

## Proposal Block Template

Use this template for each flagged item:

```
#### [F-001] [Smell Name] -- [Brief Title]

**Location**: `path/to/file.ext`, lines [start]-[end], class/method `Name`

**Current State**
- Granularity: function | class | module | cross-cutting
- Metrics: [lines, methods, deps, complexity -- whichever apply]
- Responsibilities: [list the distinct responsibilities]
- Smell(s): [God Class, Hardcoded Dependencies, etc.]

**Proposed Refactoring**
1. [Pattern/Technique]: Concise description of what to extract, split, inject, or reorganize
2. [Pattern/Technique]: ...

**Target Structure (after refactoring)**
- `NewUnitA` -- [single responsibility description]
- `NewUnitB` -- [single responsibility description]
- `InterfaceName` -- [contract / purpose]

**Dependency Injection Changes**
- `ClassName` currently instantiates `ConcreteService` --> inject `IService` via constructor
- (or: "No DI changes needed -- dependencies are already injected/pure utilities")

**Migration Notes**
- [Ordering constraints, breaking changes, intermediate steps, risk level]
- Risk: Low | Medium | High
```

## Priority Ranking Table

```
### Priority Ranking

| # | ID | Smell | Location | Impact | Effort | Technique |
|---|-----|-------|----------|--------|--------|-----------|
| 1 | F-003 | God Class | UserService.java | High | Medium | Extract Class, DI |
| 2 | F-001 | Long Method | utils.py:45-120 | High | Low | Extract Method |
| 3 | F-007 | Circular Dep | auth <-> users | High | High | Extract Interface, DIP |
| ... | ... | ... | ... | ... | ... | ... |
```

**Impact** (High / Medium / Low):
- High = Blocks feature development, causes bugs, significant maintenance burden
- Medium = Slows development, increases cognitive load, complicates onboarding
- Low = Minor inconvenience, cosmetic, low-risk

**Effort** (Low / Medium / High):
- Low = Quick fix, localized change, < 1 hour
- Medium = Touches a few files, 1-4 hours
- High = Architectural change, may require staged rollout, 4+ hours

Prioritize by impact/effort ratio: high-impact/low-effort items first.

## Example: Complete Proposal Block

```
#### [F-002] God Class + Hardcoded Dependencies -- OrderService

**Location**: `src/services/OrderService.java`, lines 1-580, class `OrderService`

**Current State**
- Granularity: class
- Metrics: 580 LOC, 14 public methods, 6 constructor params + 3 hardcoded deps
- Responsibilities: order validation, pricing/discount calculation, payment processing, email notifications, inventory updates
- Smell(s): God Class, Hardcoded Dependencies, Divergent Change

**Proposed Refactoring**
1. Extract Class: Pull validation logic (lines 45-120) into `OrderValidator`
2. Extract Class: Pull pricing logic (lines 130-210) into `PricingEngine`
3. Extract Class: Pull notification logic (lines 350-420) into `OrderNotificationService`
4. Constructor Injection: Replace `new StripeGateway()` with injected `PaymentGateway` interface
5. Constructor Injection: Replace `new SmtpEmailSender()` with injected `EmailSender` interface
6. Constructor Injection: Replace `InventoryService.getInstance()` with injected `InventoryService` interface

**Target Structure (after refactoring)**
- `OrderService` -- orchestration only: validate, price, pay, notify
- `OrderValidator` -- all validation rules and checks
- `PricingEngine` -- discount calculation, pricing tiers, tax
- `OrderNotificationService` -- email templates and sending
- `PaymentGateway` (interface) -- payment processing contract
- `EmailSender` (interface) -- email delivery contract
- `InventoryService` (interface) -- stock management contract

**Dependency Injection Changes**
- `OrderService` instantiates `StripeGateway` --> inject `PaymentGateway` via constructor
- `OrderService` instantiates `SmtpEmailSender` --> inject `EmailSender` via constructor
- `OrderService` calls `InventoryService.getInstance()` --> inject `InventoryService` via constructor
- Extracted classes (`OrderValidator`, `PricingEngine`, `OrderNotificationService`) become constructor-injected dependencies of `OrderService`

**Migration Notes**
- Extract one class at a time, starting with `OrderValidator` (least coupled)
- Each extraction is independently deployable
- Update DI container registrations after each extraction
- Risk: Medium -- high method count means careful attention to shared state
```

## Guidelines for Writing Proposals

1. **Be concrete**: Always include file paths, line ranges, method/class names. Never write "consider refactoring the large class" -- name it.
2. **Explain the why**: Each diagnosis should explain why the current structure is problematic (testability, change friction, cognitive load).
3. **Sequence the work**: Migration notes should specify which refactoring to do first and why.
4. **Always assess DI**: Every proposal must include a DI assessment, even if the answer is "No DI changes needed."
5. **Right-size proposals**: A single god class might need 3-4 extraction steps. A long method might need one Extract Method call. Match the proposal to the problem.
6. **Respect the language**: Java proposals should mention Spring/Guice registration. Python proposals should consider whether a class or module-level function is more idiomatic. TypeScript proposals should consider functional alternatives.
