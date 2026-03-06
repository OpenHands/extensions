# Structural Refactorings

Architectural-level refactoring techniques for module boundaries, circular dependencies, layering, and duplication consolidation.

## Break Circular Dependencies

Circular dependencies create fragile, hard-to-test, hard-to-deploy code. They prevent independent compilation and deployment of modules.

### Detection

1. Trace import/require/using statements across files
2. Build a directed dependency graph
3. Identify cycles: A -> B -> C -> A
4. In Python, look for lazy imports or imports inside functions (workarounds for circular imports)

### Techniques

#### Extract Interface (Dependency Inversion)

The most common approach. Break the cycle by introducing an interface at the cycle point.

```
BEFORE: A --> B --> A (circular)

AFTER:
  A --> IB (interface, owned by A's package)
  B implements IB
  B --> A (one-directional)
```

The key insight: the interface is defined in the consumer's package, not the provider's. This inverts the dependency direction.

#### Extract Shared Module

When two modules share types or contracts, extract the shared elements into a third module that both depend on.

```
BEFORE:
  auth --> users (for UserProfile type)
  users --> auth (for AuthToken type)

AFTER:
  auth --> shared-types
  users --> shared-types
  shared-types contains: UserProfile, AuthToken
```

#### Event-Based Decoupling

When both sides need to communicate, use events to break direct references.

```
BEFORE:
  OrderService --> InventoryService.reserve()
  InventoryService --> OrderService.updateStatus()

AFTER:
  OrderService publishes OrderPlacedEvent
  InventoryService listens for OrderPlacedEvent
  InventoryService publishes StockReservedEvent
  OrderService listens for StockReservedEvent
```

#### Callback / Dependency Injection

Pass behavior as a parameter instead of referencing the other module directly.

```python
# BEFORE: circular
# auth.py
from users import get_user_permissions  # circular if users imports auth

# AFTER: inject the dependency
class AuthService:
    def __init__(self, get_permissions: Callable[[str], list[str]]):
        self.get_permissions = get_permissions
```

### Sequencing

1. Map the full cycle (may be longer than 2 modules)
2. Identify the weakest link -- the dependency that's easiest to invert
3. Extract interface or shared types at that point
4. Verify the cycle is broken
5. Repeat if multiple cycles exist

## Introduce Layering

Establish clear architectural boundaries when code has become a "big ball of mud."

### Common Layer Structures

**Three-Layer Architecture:**
```
Presentation (controllers, views, CLI)
    |
Application (use cases, orchestration)
    |
Domain (entities, business rules, interfaces)
    |
Infrastructure (database, HTTP, filesystem)
```

**Dependency Rule:** Dependencies point inward. Infrastructure implements domain interfaces. Presentation depends on application. Nothing depends on presentation.

### How to Introduce Layers

1. **Identify current violations**: UI code calling database directly, business logic in controllers, infrastructure types in domain code
2. **Define interfaces at boundaries**: Domain defines `OrderRepository` interface; infrastructure implements it
3. **Move code to correct layer**: Extract business logic from controllers into application/domain layer
4. **Enforce via package structure**: Create packages/modules for each layer
5. **Apply DI**: Wire layers together via constructor injection

### Signs Layering Is Needed

- Controllers contain business logic (>20 lines beyond request/response handling)
- Domain objects import infrastructure types (database clients, HTTP libraries)
- Test setup requires standing up real infrastructure
- Changing a database query requires modifying UI code

## Consolidate Duplicates

Eliminate duplicated logic by extracting shared code into a single location.

### Detection

- Same algorithm implemented in 2+ places with minor variations
- Copy-pasted code blocks with only variable names changed
- Parallel methods across classes that do nearly the same thing

### Techniques

#### Extract Shared Function/Method

For duplicated logic within a single module:
```python
# BEFORE: duplicated validation in two methods
def create_user(data):
    if not data.get("email") or "@" not in data["email"]:
        raise ValueError("Invalid email")
    # ...

def update_user(data):
    if not data.get("email") or "@" not in data["email"]:
        raise ValueError("Invalid email")
    # ...

# AFTER: extract shared validation
def validate_email(email: str) -> None:
    if not email or "@" not in email:
        raise ValueError("Invalid email")
```

#### Extract Shared Module

For duplicated logic across packages:
1. Create a shared module (e.g., `common/validation.py`)
2. Move the duplicated logic there
3. Have both original locations import from the shared module

#### Template Method

For duplicated algorithms with varying steps:
```java
// Base class defines the algorithm skeleton
abstract class DataImporter {
    public final void importData(Source source) {
        List<Record> records = parse(source);      // varies
        List<Record> valid = validate(records);      // shared
        save(valid);                                  // varies
    }

    protected abstract List<Record> parse(Source source);
    protected abstract void save(List<Record> records);

    private List<Record> validate(List<Record> records) {
        // shared validation logic
    }
}
```

### Guidelines

- Consolidate only when the duplication is **actual** (same concept) not **accidental** (same code, different reasons to change)
- If two pieces of code look the same but evolve for different reasons, they should remain separate
- Prefer extracting functions over creating inheritance hierarchies

## Define Module Boundaries

Clarify public APIs and hide internal details to reduce coupling.

### Techniques

#### Restrict Exports

```typescript
// BEFORE: everything exported
export class InternalHelper { ... }
export class PublicService { ... }
export function internalUtil() { ... }

// AFTER: explicit public API via barrel file
// index.ts
export { PublicService } from './PublicService';
// InternalHelper and internalUtil are NOT exported
```

#### Package-Private / Internal Access

- Java: package-private (default) access modifier
- C#: `internal` keyword
- Python: `_` prefix convention for private modules
- Go: unexported names (lowercase first letter)

#### Define Contracts

- Each module exposes interfaces/types for what it provides
- Consumers depend on the contract, not the implementation
- Changes to internal implementation don't affect consumers

### Signs Boundaries Are Needed

- Consumers reach into a module's internal classes
- Refactoring one module's internals breaks other modules
- No clear "front door" to a package -- callers use many different classes
- Tight coupling makes it impossible to test modules in isolation
