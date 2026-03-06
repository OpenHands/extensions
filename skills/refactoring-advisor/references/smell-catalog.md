# Code Smell Catalog

Complete taxonomy of code smells for Phase 2 (Diagnosis). Each smell includes detection criteria, indicators, and recommended refactoring techniques.

## Bloaters

Smells where code grows excessively large.

### Long Method
- **Detection**: Function body exceeds language-adjusted threshold (30 Python, 40 TS, 50 Java/C#)
- **Indicators**: Multiple comments explaining sections, deeply nested blocks, multiple return paths, mixed abstraction levels
- **Refactoring**: Extract Method, Replace Temp with Query, Decompose Conditional, Guard Clauses

### God Class (Blob / Large Class)
- **Detection**: Class exceeds 300 LOC or 7-8+ public methods; high instance variable count (8+); low internal cohesion
- **Indicators**: Class name contains "Manager", "Handler", "Service", "Util" with unrelated methods; methods cluster into distinct groups that don't share fields
- **Refactoring**: Extract Class, Extract Interface, Constructor Injection for extracted collaborators

### God Module
- **Detection**: Module imported by >50% of other modules; contains unrelated functionality
- **Indicators**: "utils.py", "helpers.ts", "common.java" that grows unbounded
- **Refactoring**: Split into focused modules by domain, introduce package boundaries

### Long Parameter List
- **Detection**: Function accepts 4-5+ parameters
- **Indicators**: Boolean flag parameters, parameters frequently passed together, parameters representing a single concept
- **Refactoring**: Introduce Parameter Object, Preserve Whole Object, Replace Parameter with Method Call

### Primitive Obsession
- **Detection**: Repeated use of primitive types (strings, ints) for domain concepts (email, money, coordinates, IDs)
- **Indicators**: Validation logic repeated wherever the value is used; same string format checked in multiple places
- **Refactoring**: Replace Data Value with Object, Introduce Value Object, Replace Type Code with Class

### Data Clumps
- **Detection**: Same group of 3+ variables appears together in multiple places
- **Indicators**: Parallel lists, repeated parameter groups, fields that always travel together
- **Refactoring**: Extract Class, Introduce Parameter Object, Preserve Whole Object

## Object-Orientation Abusers

Smells from incomplete or incorrect use of OO principles.

### Feature Envy
- **Detection**: Method accesses fields/methods of another class more than its own
- **Indicators**: Long chains of getter calls on a single object, method logically belongs elsewhere, data and operations are separated
- **Refactoring**: Move Method, Extract Method + Move Method

### Refused Bequest
- **Detection**: Subclass uses only a few of the inherited methods/properties
- **Indicators**: Overriding methods to throw exceptions or no-op, inheriting purely for code reuse, subclass that conceptually "is not" a superclass
- **Refactoring**: Replace Inheritance with Delegation, Extract Subclass

### Switch Statements (Repeated Conditionals)
- **Detection**: Same switch/if-else chain on a type code appears in multiple places
- **Indicators**: Adding a new type requires changes in multiple locations
- **Refactoring**: Replace Conditional with Polymorphism, Strategy pattern, Replace Type Code with Strategy

### Inappropriate Intimacy
- **Detection**: Two classes access each other's private/internal details extensively
- **Indicators**: Friend classes, bidirectional references, accessing private fields via reflection, one class reaching deep into another's internals
- **Refactoring**: Move Method, Move Field, Extract Class, Hide Delegate, define clear public APIs

### Parallel Inheritance Hierarchies
- **Detection**: Creating a subclass in one hierarchy requires creating a subclass in another
- **Indicators**: Matching class name prefixes across hierarchies
- **Refactoring**: Move Method, Move Field to consolidate hierarchies

## Change Preventers

Smells that make changes difficult and risky.

### Divergent Change
- **Detection**: One class is modified for multiple unrelated reasons
- **Indicators**: Separate groups of methods changed for different features; class has multiple axes of change
- **Refactoring**: Extract Class (one class per axis of change), Single Responsibility Principle

### Shotgun Surgery
- **Detection**: A single logical change requires editing many classes/files
- **Indicators**: Adding a field requires changes in 5+ files; feature toggles scattered everywhere; one business rule spread across layers
- **Refactoring**: Move Method, Move Field, Inline Class to consolidate, Extract Module

### Rigidity / Fragility
- **Detection**: Small changes cascade through the system; fixing one thing breaks another
- **Indicators**: High coupling metrics, missing abstraction layers, no interface boundaries
- **Refactoring**: Extract Interface, Dependency Injection, Introduce Facade, define module boundaries

## Dispensables

Smells representing unnecessary code.

### Duplicated Code
- **Detection**: Near-identical code blocks (3+ lines) in multiple locations
- **Indicators**: Copy-paste patterns, similar methods with minor variations, same algorithm implemented slightly differently in different files
- **Refactoring**: Extract Method, Pull Up Method, Form Template Method, Extract shared module

### Dead Code
- **Detection**: Unreachable methods, unused variables, commented-out blocks, unexecuted branches
- **Indicators**: No callers found, `// TODO: remove` comments, feature flags for features long since launched
- **Refactoring**: Remove (after confirming no dynamic/reflective usage)

### Speculative Generality
- **Detection**: Abstract classes, interfaces, or parameters that serve only one concrete case
- **Indicators**: "Future-proofing" with no current second implementation; unused hooks/callbacks; parameterized code that's only ever called one way
- **Refactoring**: Collapse Hierarchy, Inline Class, Remove Parameter

### Lazy Class
- **Detection**: Class that does too little to justify its existence
- **Indicators**: Wrapper class adding no value, thin proxy with no logic, class with 1-2 trivial methods
- **Refactoring**: Inline Class, Collapse Hierarchy

## Couplers

Smells related to excessive coupling between components.

### Hardcoded Dependencies
- **Detection**: Class creates its own collaborators via `new`, static calls, or singleton access
- **Indicators**: `new DatabaseClient()` in business logic, `Logger.getInstance()`, `ServiceLocator.resolve()`, module-level global instances
- **Refactoring**: Constructor Injection behind interface, Factory for runtime-determined dependencies
- **Note**: This is always worth flagging, even in otherwise-clean code

### Message Chains
- **Detection**: `a.getB().getC().getD().doSomething()` -- long chains of method calls
- **Indicators**: Client depends on internal structure of object graphs
- **Refactoring**: Hide Delegate, Extract Method, Move Method, Law of Demeter

### Middle Man
- **Detection**: Class that delegates most of its work to another class
- **Indicators**: Methods that just call through to a single delegate
- **Refactoring**: Remove Middle Man, Inline Method, Replace Delegation with Inheritance

### Circular Dependencies
- **Detection**: Module A depends on Module B, which depends back on A (directly or transitively)
- **Indicators**: Import cycles, bidirectional references between packages, lazy imports as workarounds
- **Refactoring**: Extract Interface, Dependency Inversion, Extract Shared Module, Event-based Decoupling

### Fat Interface
- **Detection**: Interface with 10+ methods; clients implement many unused methods
- **Indicators**: Empty/no-op implementations, partial interface usage
- **Refactoring**: Interface Segregation, split into role-specific interfaces

### Leaky Abstraction
- **Detection**: Internal implementation details exposed through public API
- **Indicators**: Callers must understand internal state to use the class correctly; implementation types in public signatures; error types that expose internal mechanisms
- **Refactoring**: Extract Interface, Hide Delegate, wrap implementation details

## Complexity Smells

### Arrow Code (Deep Nesting)
- **Detection**: Nesting depth exceeds 3 levels
- **Indicators**: Code forms a visual "arrow" pointing right; difficult control flow
- **Refactoring**: Guard Clauses (early return), Extract Method, Replace Conditional with Polymorphism

### Boolean Blindness
- **Detection**: Methods accepting multiple boolean parameters
- **Indicators**: Call sites like `process(true, false, true)` that are unreadable without checking the signature
- **Refactoring**: Replace Boolean with Enum, Introduce Parameter Object, Replace with Explicit Methods

### Magic Numbers / Strings
- **Detection**: Literal values used directly in logic without named constants
- **Indicators**: Same literal in multiple places; meaning not self-evident from context
- **Refactoring**: Replace Magic Number with Symbolic Constant, Extract Constant

### Temporal Coupling
- **Detection**: Methods that must be called in a specific order with no compile-time enforcement
- **Indicators**: `init()` must be called before `process()`; state machine with implicit transitions
- **Refactoring**: Builder pattern, combine into single method, make illegal states unrepresentable
