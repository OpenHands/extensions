# Classic Refactorings

Catalog of established refactoring techniques. Each entry describes when to apply, mechanics, and a brief example.

## Extract Method / Function

**When**: A code fragment can be grouped and given a meaningful name. Comments above a block often indicate extraction opportunities.

**Mechanics**: Identify the fragment, create a new method with a descriptive name, move the code, pass needed variables as parameters, return computed values.

```python
# BEFORE
def process_order(order):
    # validate
    if not order.items:
        raise ValueError("Empty order")
    if order.total < 0:
        raise ValueError("Invalid total")
    # calculate discount
    discount = 0
    if order.total > 100:
        discount = order.total * 0.1
    elif order.total > 50:
        discount = order.total * 0.05
    order.total -= discount
    # save
    db.save(order)

# AFTER
def process_order(order):
    validate_order(order)
    apply_discount(order)
    db.save(order)

def validate_order(order):
    if not order.items:
        raise ValueError("Empty order")
    if order.total < 0:
        raise ValueError("Invalid total")

def apply_discount(order):
    if order.total > 100:
        order.total *= 0.9
    elif order.total > 50:
        order.total *= 0.95
```

## Extract Class / Module

**When**: A class has multiple distinct responsibilities. Fields and methods cluster into groups that don't interact.

**Mechanics**: Identify clusters of related fields/methods, create a new class for each cluster, move members, establish relationships. Make the original class delegate to extracted classes.

**Combines with DI**: Extracted classes become constructor-injected dependencies of the original.

## Introduce Parameter Object

**When**: A group of parameters frequently travels together across method signatures.

**Mechanics**: Create a class/record/dataclass to bundle the parameters. Replace individual parameters.

```typescript
// BEFORE
function createUser(name: string, email: string, age: number, country: string, role: string) { ... }

// AFTER
interface CreateUserRequest {
    name: string;
    email: string;
    age: number;
    country: string;
    role: string;
}
function createUser(request: CreateUserRequest) { ... }
```

## Move Method / Move Field

**When**: A method/field is used more by another class than its own (Feature Envy).

**Mechanics**: Copy to the class that uses it most, adjust references, remove the original. If the method references data from both classes, pass the less-used class's data as a parameter.

## Replace Conditional with Polymorphism

**When**: Same type-based switch/if-else chain appears in multiple places.

**Mechanics**: Create a class hierarchy or strategy interface. Each branch becomes a class with its own implementation.

```java
// BEFORE
double calculatePay(Employee e) {
    switch (e.type) {
        case ENGINEER: return e.salary;
        case MANAGER: return e.salary + e.bonus;
        case SALES: return e.salary + e.commission;
    }
}

// AFTER
interface Employee {
    double calculatePay();
}
class Engineer implements Employee {
    public double calculatePay() { return salary; }
}
class Manager implements Employee {
    public double calculatePay() { return salary + bonus; }
}
```

## Replace Inheritance with Delegation

**When**: A subclass only uses part of the parent interface (Refused Bequest), or inheritance is used purely for code reuse.

**Mechanics**: Create a field for the former parent class. Delegate specific methods. Remove inheritance.

## Guard Clauses (Replace Nested Conditional)

**When**: Deep nesting from sequential conditions creates arrow code.

**Mechanics**: Invert conditions and return/throw early to flatten the structure.

```csharp
// BEFORE
public decimal CalculateDiscount(Order order)
{
    if (order != null)
    {
        if (order.Customer != null)
        {
            if (order.Customer.IsPremium)
            {
                if (order.Total > 100)
                {
                    return order.Total * 0.2m;
                }
            }
        }
    }
    return 0;
}

// AFTER
public decimal CalculateDiscount(Order order)
{
    if (order == null) return 0;
    if (order.Customer == null) return 0;
    if (!order.Customer.IsPremium) return 0;
    if (order.Total <= 100) return 0;

    return order.Total * 0.2m;
}
```

## Extract Interface

**When**: Multiple classes share common operations, or a class needs to be decoupled from concrete dependencies.

**Mechanics**: Identify common methods, create an interface, have classes implement it, program to the interface.

**Key for DI**: Extracting interfaces is often the prerequisite step before introducing constructor injection.

## Inline Class / Collapse Hierarchy

**When**: A class does too little (Lazy Class) or is a needless Middle Man. Or a subclass adds no behavior over its parent.

**Mechanics**: Move all features into the using class, delete the empty class.

## Invert Dependencies (Dependency Inversion Principle)

**When**: A high-level module depends on a low-level module's concrete type.

**Mechanics**: Define an interface owned by the high-level module. Have the low-level module implement it. The dependency arrow now points from low-level to high-level.

```
BEFORE: OrderService --> SqlOrderRepository
AFTER:  OrderService --> OrderRepository (interface)
                              ^
                              |
                    SqlOrderRepository (implements)
```

## Replace Temp with Query

**When**: A temporary variable holds the result of an expression that could be a method call.

**Mechanics**: Extract the expression into a method. Replace all references to the temp with the method call.

## Decompose Conditional

**When**: A complex conditional expression makes the code hard to read.

**Mechanics**: Extract the condition and each branch into separate methods with intention-revealing names.

```python
# BEFORE
if date.before(SUMMER_START) or date.after(SUMMER_END):
    charge = quantity * winter_rate + winter_service_charge
else:
    charge = quantity * summer_rate

# AFTER
if is_winter(date):
    charge = winter_charge(quantity)
else:
    charge = summer_charge(quantity)
```
