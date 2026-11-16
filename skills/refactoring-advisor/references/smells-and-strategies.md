# Smells and Refactoring Strategies

Use this catalog to name a diagnosis consistently. Select only smells supported by repository evidence.

| Smell | Typical evidence | Likely root cause | Candidate strategies |
| --- | --- | --- | --- |
| Long Method | Multiple phases, mixed abstraction, many branches or locals | Missing workflow steps or domain concepts | Extract Function, Replace Temp with Query, Decompose Conditional |
| Long Parameter List | Repeated parameter groups, boolean flags, unstable call sites | Missing parameter object or hidden collaborator | Introduce Parameter Object, Preserve Whole Object, inject a collaborator |
| God Class / Large Class | Unrelated field and method clusters, many reasons to change | Responsibilities accumulated around a convenient coordinator | Extract Class, Extract Module, Move Method, Facade |
| Feature Envy | Logic reads another object's data more than its own | Behavior lives outside the concept it governs | Move Function, Extract Function, domain service when ownership spans concepts |
| Data Clumps | Same values travel together across APIs | Missing value object or request concept | Extract Class, Introduce Parameter Object |
| Primitive Obsession | Domain rules repeated around strings, numbers, or flags | Missing domain type | Replace Primitive with Object, Value Object |
| Switch Statements / Repeated Conditionals | Same type or state branching repeated in many places | Missing polymorphic behavior or dispatch table | Replace Conditional with Polymorphism, Strategy, State; keep a switch when it is localized and stable |
| Divergent Change | One module changes for unrelated reasons | Responsibilities share a physical boundary without conceptual cohesion | Extract Module or Class, Separate Query from Modifier |
| Shotgun Surgery | One policy change touches many modules | Scattered ownership or leaky abstraction | Move Function, Inline then re-extract around one owner, Facade |
| Duplicated Code | Same rule or transformation implemented in several places | No authoritative owner or premature copying | Extract Function, Pull Up Method, shared domain policy; avoid generic utilities without cohesion |
| Inappropriate Intimacy | Modules reach into internals or share mutable state | Boundary exposes representation instead of behavior | Move Function, Hide Delegate, Encapsulate Variable |
| Message Chains | Callers traverse deep object graphs | Missing operation at the owning boundary | Hide Delegate, Extract Function; avoid wrappers that only mirror the chain |
| Middle Man | A type delegates nearly everything without policy | Layer exists without responsibility | Remove Middle Man, Inline Class |
| Leaky Abstraction | Callers understand transport, storage, or framework details | Contract does not contain volatility | Extract Interface, Adapter, Repository, Anti-Corruption Layer |
| Circular Dependency | Packages import each other directly or indirectly | Responsibilities or shared contracts are placed on the wrong side | Move shared contract, Dependency Inversion, domain events, merge falsely separated modules |
| Service Locator / Hidden Dependency | Global lookup, static singleton, ambient context | Construction and use are conflated | Constructor or parameter injection, composition root |
| Temporal Coupling | Calls must occur in an undocumented order | Invalid intermediate states or split lifecycle ownership | Encapsulate lifecycle, factory, state object, command |
| Parallel Inheritance Hierarchies | Adding one subtype requires a matching subtype elsewhere | Two variation axes are encoded as inheritance | Move Method, Strategy, composition |
| Speculative Generality | Unused abstractions, one-implementation interfaces, configurable paths with no consumer | Future-proofing without evidence | Collapse Hierarchy, Inline Class, remove dead abstraction |
| Mutable Global State | Tests depend on order or process-wide mutation | Ownership and lifecycle are implicit | Inject state holder, immutable configuration, scoped context |
| Mixed I/O and Domain Logic | Business decisions occur inside HTTP, DB, filesystem, or UI code | Missing application boundary | Extract Function or Service, Ports and Adapters, inject gateway |

## Dependency Injection Decision

Evaluate DI for every proposal with these questions:

1. Does the target directly create or locate a volatile dependency such as a database, network client, filesystem, clock, random source, environment, queue, or framework service?
2. Does substituting that dependency materially improve deterministic tests or support multiple implementations?
3. Is there a clear composition root that can own construction and lifecycle?
4. Can a function parameter or constructor argument solve the problem without a container or new interface?
5. Would injection expose a real architectural boundary, or merely move cohesive internal details into the caller?

Recommend, in order of simplicity:

1. Parameter injection for a dependency used by one operation.
2. Constructor injection for a stable collaborator used across instance operations.
3. Factory injection when creation timing or per-operation configuration varies.
4. Framework-native registration when the application already uses a DI framework and lifecycle management matters.

Mark DI as `Not needed` when the proposal concerns a pure computation, a cohesive value object, internal deterministic helpers, or an extraction with no external dependency. Explain the specific reason.

Avoid:

- injecting every helper or value object;
- creating interfaces solely to mock a class with no volatility;
- adding a service locator disguised as an injector;
- passing a general container into domain code;
- changing singleton lifetime without accounting for state and concurrency;
- recommending DI as a substitute for choosing the correct responsibility boundary.

## Pattern Selection Guardrail

Name a pattern only after identifying the force it resolves:

- Use **Strategy** for a genuine, selectable algorithm family.
- Use **State** when allowed behavior changes with explicit lifecycle state.
- Use **Adapter** to translate an external or legacy contract.
- Use **Facade** to present a cohesive entry point over a complicated subsystem.
- Use **Repository** to isolate persistence semantics, not as a generic wrapper over every query.
- Use **Decorator** for independently composable behavior around a stable contract.
- Use **Command** when operations need queuing, logging, retries, undo, or independent dispatch.
- Use **Ports and Adapters** when domain policy must remain independent of multiple volatile external systems.

Prefer Extract Function, Move Function, Extract Class, or Introduce Parameter Object when those operations solve the problem without a larger pattern.
