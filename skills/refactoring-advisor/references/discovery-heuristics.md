# Discovery Heuristics

Detection thresholds and scanning methodology for Phase 1 (Discovery). Adapt all thresholds to the language, framework, and project context.

## Function-Level Signals

| Signal | Default Threshold | Notes |
|--------|------------------|-------|
| Lines of code | > 50 | Python: > 30, Java/C#: > 50, TypeScript: > 40 |
| Parameters | > 4-5 | Lower if language supports named/keyword arguments |
| Nesting depth | > 3 levels | if inside if inside for inside try = arrow code |
| Cyclomatic complexity | High branch count | Multiple return paths, deeply nested conditionals |
| Mixed abstraction levels | I/O + logic + formatting | One function doing file reads, business logic, and string formatting |
| Flag-driven branching | Boolean params controlling flow | `process(data, validate=True, log=True, dry_run=False)` |

### What to Look For

- **Comment-delimited sections**: Comments like `// validate`, `// calculate`, `// save` inside a function indicate extractable blocks
- **Multiple return paths**: Functions with 4+ return statements often have complex control flow
- **Deeply nested blocks**: Code forming a visual "arrow" pointing right
- **Duplicated logic**: Near-identical code blocks (3+ lines) across functions
- **Boolean parameters**: Functions that behave completely differently based on flag arguments

## Class-Level Signals

| Signal | Default Threshold | Notes |
|--------|------------------|-------|
| Lines of code | > 300 | C# partial classes may inflate; focus on logical size |
| Public methods | > 7-8 | Excludes property accessors in C#/Java |
| Constructor dependencies | > 5-6 | Count injected + hardcoded dependencies |
| Instance variables | > 8 | High field count suggests multiple responsibilities |
| Mixed responsibilities | 2+ distinct concerns | Methods cluster into unrelated groups |
| Low cohesion | Methods don't share state | Subsets of methods use disjoint subsets of fields |

### What to Look For

- **Name hints**: Classes named "Manager", "Handler", "Service", "Util", "Helper" with many unrelated methods
- **Responsibility clusters**: Groups of methods + fields that could be extracted as a unit
- **Constructor explosion**: Constructor that creates its own collaborators via `new`
- **God class indicators**: Class imported/used by many other classes across the project
- **Anemic domain models**: Data classes with only getters/setters and no behavior

## Module / Package-Level Signals

| Signal | Detection Method |
|--------|-----------------|
| Circular dependencies | Trace import chains: A imports B imports A (or longer cycles) |
| God modules | One module imported by >50% of other modules |
| Feature scatter | Implementing one feature requires touching 5+ files across packages |
| Layering violations | Presentation layer importing database layer directly |
| Duplicated logic | Similar functions/classes appearing in multiple modules |
| Barrel file explosion | Re-export files that obscure actual dependency structure (TypeScript) |

### How to Detect Circular Dependencies

1. Trace import/require/using statements across files
2. Build a directed graph of module dependencies
3. Look for cycles (A -> B -> C -> A)
4. Check for indirect cycles through shared modules
5. In Python, look for `ImportError` workarounds (lazy imports, imports inside functions)

## Dependency and Coupling Signals

| Signal | What to Flag |
|--------|-------------|
| Hardcoded instantiation | `new Service()`, `Service()`, direct constructor calls for collaborators |
| Static service calls | `Database.query()`, `Logger.log()`, `Cache.get()` |
| Singleton access | `Instance.getInstance()`, `shared`, module-level global instances |
| Service locator | `container.resolve()`, `ServiceLocator.get()` in business logic |
| Ambient context | `DateTime.Now`, `HttpContext.Current`, thread-local state |
| Concrete-type coupling | Method signatures accepting `MySqlDatabase` instead of `Database` interface |
| Hidden dependencies | Globals, module-level state, environment variable reads deep in logic |

### DI Evaluation Checklist

For every coupling signal, evaluate:

1. **Is this a collaborator or a value?** Collaborators (services, repositories, gateways) should be injected. Values (strings, numbers, config constants) should be passed as parameters.
2. **Does this have side effects?** If yes, injection makes it testable.
3. **Could this need substitution?** In tests, in different environments, for different configurations -- if yes, inject it.
4. **Is this a pure utility?** String formatting, math operations, pure transformations -- these don't need injection.

## Language-Specific Calibration

### Java
- Function length: 50 LOC (Java is inherently verbose)
- Watch for: excessive getter/setter boilerplate (consider records or Lombok), checked exception abuse, overuse of inheritance
- God Class: 500 LOC / 10 public methods (higher threshold due to verbosity)
- DI is idiomatic: Spring, Guice, Dagger are standard

### Python
- Function length: 30 LOC (Python idiom favors shorter functions)
- Watch for: oversized `__init__` methods, module-level global state, circular imports, `**kwargs` hiding signatures
- God Class: 300 LOC / 8 public methods
- DI via constructor `__init__` or dependency-injector library; module-level functions can substitute for classes

### TypeScript
- Function length: 40 LOC
- Watch for: `any` type overuse, barrel file explosion, deep re-export chains, side effects in module scope
- Class size: 400 LOC (TS projects often favor functional style)
- DI frameworks: InversifyJS, tsyringe, NestJS built-in DI

### C#
- Function length: 50 LOC
- Watch for: service locator anti-pattern, static class abuse, partial classes masking god classes
- God Class: 500 LOC / 10 public methods
- DI is first-class: Microsoft.Extensions.DependencyInjection, Autofac, Ninject

### Go
- Function length: 40 LOC
- Watch for: giant `switch` statements, error handling boilerplate inflating function length, package-level variables
- DI via constructor functions returning interfaces; no framework needed
- Interfaces are implicit -- recommend defining small consumer-side interfaces

### Rust
- Function length: 50 LOC
- Watch for: deeply nested `match` chains, overly generic trait bounds, large `impl` blocks
- DI via trait objects or generics; constructor injection through `new()` functions accepting trait bounds

## False Positive Avoidance

### Do Not Flag

- **Generated code**: protobuf stubs, ORM migrations, auto-generated API clients, GraphQL codegen
- **Test files**: Tests may intentionally duplicate setup for readability; only flag when duplication is genuinely harmful
- **Framework-mandated patterns**: Django views inheriting from generic views, Spring `@Controller` classes, React component boilerplate
- **Configuration/declarative code**: YAML, JSON configs, route tables, DI container registrations
- **Data transfer objects**: DTOs, request/response types, and serialization models are inherently "data classes" by design
- **Entry points**: `main()` functions, CLI argument parsing, server bootstrap code may legitimately be long

### Calibrate, Don't Blindly Apply

- A 60-line function in Java with clear structure may be fine; a 35-line function in Python with deep nesting is not
- Parameter count thresholds shift with named/keyword arguments
- Class size norms differ by paradigm: OOP-heavy Java vs. functional TypeScript
- A class with 10 methods where all methods share state is cohesive -- not a god class
